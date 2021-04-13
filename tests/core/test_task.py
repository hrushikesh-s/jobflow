from uuid import uuid4

import pytest


def add(a, b=5):
    from jobflow.core.outputs import Number

    return Number(a + b)


def test_task_init():
    from jobflow.core.outputs import Dynamic, Number
    from jobflow.core.task import Task

    # test basic init
    test_task = Task(function=("builtins", "print"), args=("I am a job",))
    assert test_task
    assert test_task.function == ("builtins", "print")
    assert test_task.function_args == ("I am a job",)
    assert test_task.function_kwargs == {}
    assert test_task.uuid is not None
    assert isinstance(test_task.outputs, Dynamic)

    # test init with outputs
    test_task = Task(
        function=(__name__, "add"), args=(1,), kwargs={"b": 2}, outputs=Number
    )
    assert test_task
    assert test_task.function == (__name__, "add")
    assert test_task.function_args == (1,)
    assert test_task.function_kwargs == {"b": 2}
    assert test_task.uuid is not None
    assert isinstance(test_task.outputs, Number)
    assert test_task.uuid == test_task.outputs.value.uuid


def test_task_run(capsys):
    from jobflow.core.outputs import Number
    from jobflow.core.reference import OutputReference
    from jobflow.core.task import Task

    # test basic run
    test_task = Task(function=("builtins", "print"), args=("I am a job",))
    response = test_task.run()
    assert capsys.readouterr().out == "I am a job\n"
    assert type(response).__name__ == "Response"

    # test run with outputs
    test_task = Task(
        function=(__name__, "add"), args=(1,), kwargs={"b": 2}, outputs=Number
    )
    response = test_task.run()
    assert type(response).__name__ == "Response"
    assert isinstance(response.outputs, Number)
    assert response.outputs.value == 3

    # test run with input references
    ref = OutputReference(uuid4(), "b")
    test_task = Task(
        function=(__name__, "add"), args=(1,), kwargs={"b": ref}, outputs=Number
    )
    response = test_task.run(output_cache={ref.uuid: {ref.name: 2}})
    assert type(response).__name__ == "Response"
    assert isinstance(response.outputs, Number)
    assert response.outputs.value == 3


def test_task_input_references():
    from jobflow.core.outputs import Number
    from jobflow.core.reference import OutputReference
    from jobflow.core.task import Task

    ref = OutputReference(uuid4(), "b")
    test_task = Task(
        function=(__name__, "add"), args=(1,), kwargs={"b": ref}, outputs=Number
    )
    references = test_task.input_references

    assert set(references) == {ref}


def test_task_output_references():
    from jobflow.core.outputs import Number
    from jobflow.core.task import Task

    test_task = Task(
        function=(__name__, "add"), args=(1,), kwargs={"b": 2}, outputs=Number
    )
    references = test_task.output_references

    assert set(references) == {test_task.outputs.value}


def test_task_resolve_args(output_store):
    from jobflow.core.reference import OutputReference
    from jobflow.core.task import Task

    # test basic run with no references
    test_task = Task(function=("builtins", "print"), args=("I am a job",))
    resolved_task = test_task.resolve_args()
    assert test_task == resolved_task

    ref = OutputReference(uuid4(), "b")
    cache = {ref.uuid: {ref.name: 2}}

    # test run with input references
    test_task = Task(function=(__name__, "add"), args=(1,), kwargs={"b": ref})
    resolved_task = test_task.resolve_args(output_cache=cache)
    assert test_task == resolved_task
    assert resolved_task.function_kwargs["b"] == 2

    # test resolve with inplace=False
    test_task = Task(function=(__name__, "add"), args=(1,), kwargs={"b": ref})
    resolved_task = test_task.resolve_args(output_cache=cache, inplace=False)
    assert test_task != resolved_task
    assert resolved_task.function_kwargs["b"] == 2
    assert isinstance(test_task.function_kwargs["b"], OutputReference)

    # test resolve with allow errors
    test_task = Task(function=(__name__, "add"), args=(1,), kwargs={"b": ref})
    resolved_task = test_task.resolve_args(output_cache={}, error_on_missing=False)
    assert test_task == resolved_task
    assert resolved_task.function_kwargs["b"] == ref

    # test resolve with store
    output_store.update({"uuid": str(ref.uuid), ref.name: 2}, key="uuid")
    test_task = Task(function=(__name__, "add"), args=(1,), kwargs={"b": ref})
    resolved_task = test_task.resolve_args(output_store=output_store)
    assert resolved_task.function_kwargs["b"] == 2

    # test cache is preferred over store
    output_store.update({"uuid": str(ref.uuid), ref.name: 10}, key="uuid")
    test_task = Task(function=(__name__, "add"), args=(1,), kwargs={"b": ref})
    resolved_task = test_task.resolve_args(
        output_store=output_store, output_cache=cache
    )
    assert resolved_task.function_kwargs["b"] == 2


def test_task_decorator():
    from jobflow.core.outputs import Dynamic, Number
    from jobflow.core.task import task

    # test basic init
    decorated = task(print)
    test_task = decorated("I am a job")
    assert test_task
    assert test_task.function == ("builtins", "print")
    assert test_task.function_args == ("I am a job",)
    assert test_task.function_kwargs == {}
    assert test_task.uuid is not None
    assert isinstance(test_task.outputs, Dynamic)

    # test init with outputs
    decorated = task(add, outputs=Number)
    test_task = decorated(1, b=2)
    assert test_task
    assert test_task.function == (__name__, "add")
    assert test_task.function_args == (1,)
    assert test_task.function_kwargs == {"b": 2}
    assert test_task.uuid is not None
    assert isinstance(test_task.outputs, Number)
    assert test_task.uuid == test_task.outputs.value.uuid

    # test applying the decorator without arguments
    @task
    def print_message(message):
        print(message)

    test_task = print_message("I am a job")
    assert test_task
    assert test_task.function == (__name__, "print_message")
    assert test_task.args == ("I am a job",)
    assert test_task.kwargs == {}
    assert test_task.uuid is not None
    assert isinstance(test_task.outputs, Dynamic)

    # test applying the decorator with arguments
    @task(outputs=Number)
    def add_numbers(a, b=10):
        return Number(a + b)

    test_task = add_numbers(1, b=2)
    assert test_task
    assert test_task.function == (__name__, "add_numbers")
    assert test_task.function_args == (1,)
    assert test_task.function_kwargs == {"b": 2}
    assert test_task.uuid is not None
    assert isinstance(test_task.outputs, Number)
    assert test_task.uuid == test_task.outputs.value.uuid

    # test setting outputs to None
    @task(outputs=None)
    def add_numbers(a, b=10):
        print(a + b)

    test_task = add_numbers(1, b=2)
    assert test_task.outputs is None


def test_task_response():
    # no need to test init as it is just a dataclass, instead test from_task_returns
    # test no job returns
    from jobflow.core.activity import Activity
    from jobflow.core.outputs import Dynamic, Number, Value
    from jobflow.core.task import Detour, Stop, Store, TaskResponse

    response = TaskResponse.from_task_returns(None)
    assert response == TaskResponse()

    # test single output
    response = TaskResponse.from_task_returns(1)
    assert isinstance(response.outputs, Value)
    assert response.outputs.value == 1

    # test list output
    response = TaskResponse.from_task_returns([1, 2, 3])
    assert isinstance(response.outputs, Value)
    assert response.outputs.value == [1, 2, 3]

    # test tuple output
    response = TaskResponse.from_task_returns((1, 2, 3))
    assert isinstance(response.outputs, Value)
    assert response.outputs.value == (1, 2, 3)

    # test dict output
    response = TaskResponse.from_task_returns({"a": 1, "b": 2})
    assert isinstance(response.outputs, Dynamic)
    assert response.outputs.a == 1
    assert response.outputs.b == 2

    # test outputs
    outputs = Number(5)
    response = TaskResponse.from_task_returns(outputs)
    assert response == TaskResponse(outputs=outputs)

    # test detour
    detour = Detour(Activity())
    response = TaskResponse.from_task_returns(detour)
    assert response == TaskResponse(detour=detour.activity)

    # test store
    store = Store({"my_data": 123})
    response = TaskResponse.from_task_returns(store)
    assert response == TaskResponse(store=store.data)

    # test stop
    stop = Stop(stop_tasks=True, stop_children=True, stop_activities=True)
    response = TaskResponse.from_task_returns(stop)
    assert response == TaskResponse(
        stop_tasks=True, stop_activities=True, stop_children=True
    )

    # test multiple
    response = TaskResponse.from_task_returns((outputs, store, stop))
    assert response == TaskResponse(
        outputs=outputs,
        store=store.data,
        stop_tasks=True,
        stop_activities=True,
        stop_children=True,
    )

    # test multiple with no outputs class
    response = TaskResponse.from_task_returns((123, store, stop))
    assert response == TaskResponse(
        outputs=Value(123),
        store=store.data,
        stop_tasks=True,
        stop_activities=True,
        stop_children=True,
    )

    # test detour overrides outputs
    response = TaskResponse.from_task_returns((outputs, detour, store, stop))
    assert response == TaskResponse(
        outputs=None,
        detour=detour.activity,
        store=store.data,
        stop_tasks=True,
        stop_activities=True,
        stop_children=True,
    )

    # test malformed outputs
    with pytest.raises(ValueError):
        TaskResponse.from_task_returns([1, 2, 3, store])

    # test multiple of the same outputs
    with pytest.raises(ValueError):
        TaskResponse.from_task_returns((store, store))

    with pytest.raises(ValueError):
        TaskResponse.from_task_returns((detour, detour))


#
# # print("calling method")
# a = maker.make(1, 2)
#
#
# class Test:
#
#     @job
#     @staticmethod
#     def static_before(a, b):
#         return a + b
#
#     @staticmethod
#     @job
#     def static_after(a, b):
#         return a + b
#
#     @job
#     @classmethod
#     def class_before(cls, a, b):
#         return a + b
#
#     @classmethod
#     @job
#     def class_after(cls, a, b):
#         return a + b
#
#
# # print("calling static after")
# a = Test.static_after(3, 4)
# # print("calling static before")
# a = Test.static_before(3, 4)
# #
# # print("calling class after")
# a = Test.class_after(3, 4)
# # print("calling class before")
# a = Test.class_before(3, 4)
#
# output = run_locally(a)
# print(list(output.values())[0])
#
