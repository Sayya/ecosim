from typing import List, Dict, Tuple

def type_check(func):
    def wapper(*args, **keywords):
        if not hasattr(func, "__annotations__"):
            message = "#1: There is no annotation."
            raise FuncTypeError(message)
        for arg, fanno in zip(args[1:], func.__annotations__.values()):
            if hasattr(fanno, "__origin__") and type(arg) is fanno.__origin__:
                type_condition(arg, fanno)
            elif type(arg) is not fanno:
                message = "#2: Annotation is {0} but arg is {1}.".format(fanno, type(arg))
                raise FuncTypeError(message)
        return func(*args, **keywords)
    return wapper

def type_condition(arg, fanno):
    origin = fanno.__origin__
    origin_args = fanno.__args__
    if origin is list:
        for a in arg:
            if type(a) is not origin_args[0]:
                message = "#3: Annotation is {0} but arg is {1}.".format(origin_args[0], type(a))
                raise FuncTypeError(message)
    elif origin is dict:
        for k, v in arg.items:
            if type(k) is not origin_args[0] or type(v) is not origin_args[1]:
                message = "#4: Annotation is {0} but arg is {1}.".format(origin_args, (type(k),type(v)))
                raise FuncTypeError(message)
    else:
        message = "#0: Annotation {0} is not registered.".format(origin)
        raise FuncTypeError(message)

class FuncTypeError(Exception):
    def __init__(self, message):
        self.message = message
