import builtins
import dis
import types
import typing as tp
class Frame:
    """
    Frame header in cpython with description
        https://github.com/python/cpython/blob/3.12/Include/internal/pycore_frame.h

    Text description of frame parameters
        https://docs.python.org/3/library/inspect.html?highlight=frame#types-and-members
    """
    def __init__(self,
                 frame_code: types.CodeType,
                 frame_builtins: dict[str, tp.Any],
                 frame_globals: dict[str, tp.Any],
                 frame_locals: dict[str, tp.Any]) -> None:
        self.code = frame_code
        self.builtins = frame_builtins
        if not isinstance(self.builtins, dict):
            self.builtins = frame_builtins.__dict__
        self.globals = frame_globals
        self.locals = frame_locals
        self.data_stack: tp.Any = []
        self.kw = None
        #for cycle
        self.ind_op = 0
        self.instructions = []
        self.offset_to_index = dict()
        self.return_value = None

    def top(self) -> tp.Any:
        return self.data_stack[-1]

    def pop(self) -> tp.Any:
        return self.data_stack.pop()
    def peek(self) -> tp.Any:
        return self.data_stack[-1]
    def push(self, *values: tp.Any) -> None:
        self.data_stack.extend(values)

    def popn(self, n: int) -> tp.Any:
        """
        Pop a number of values from the value stack.
        A list of n values is returned, the deepest value first.
        """
        if n > 0:
            returned = self.data_stack[-n:]
            self.data_stack[-n:] = []
            return returned
        else:
            return []
    def run(self) -> None:
        self.instructions = list(dis.get_instructions(self.code))
        self.offset_to_index = {instr.offset: i for i, instr in enumerate(self.instructions)}
        while self.ind_op < len(self.instructions):
            instr = self.instructions[self.ind_op]
            opname = instr.opname.lower()
            old_ind = self.ind_op
            if opname == 'return_value':
                return self.pop()
            elif opname == 'load_attr':
                getattr(self, opname)(instr.arg)
            else:
                getattr(self, opname)(instr.argval)
            if self.ind_op == old_ind:
                self.ind_op += 1

    def resume(self, arg: int) -> tp.Any:
        pass

    def push_null(self, arg: int) -> tp.Any:
        pass
        #self.push(None)

    def precall(self, arg: int) -> tp.Any:
        pass

    def call(self, arg: int) -> None:
        """
        Operation description:
            https://docs.python.org/release/3.12.5/library/dis.html#opcode-CALL
        """
        arguments = self.popn(arg)
        f = self.pop()
        self.push(f(*arguments))

    def load_name(self, arg: str) -> None:
        """
        Partial realization

        Operation description:
            https://docs.python.org/release/3.12.5/library/dis.html#opcode-LOAD_NAME
        """
        if arg in self.locals:
            self.push(self.locals[arg])
        elif arg in self.globals:
            self.push(self.globals[arg])
        elif arg in self.builtins:
            self.push(self.builtins[arg])
        else:
            raise NameError(f"Name '{arg}' not in scope.")

    def load_global(self, arg: str) -> None:
        """
        Operation description:
            https://docs.python.org/release/3.12.5/library/dis.html#opcode-LOAD_GLOBAL
        """
        if arg in self.globals:
            self.push(self.globals[arg])
        elif arg in self.builtins:
            self.push(self.builtins[arg])
        else:
            raise NameError(f"Name '{arg}' not in scope.")

    def load_const(self, arg: tp.Any) -> None:
        """
        Operation description:
            https://docs.python.org/release/3.12.5/library/dis.html#opcode-LOAD_CONST
        """
        self.push(arg)

    def load_fast(self, arg: str) -> None:
        self.push(self.locals[arg])

    def return_value(self, arg: tp.Any) -> None:
        """
        Operation description:
            https://docs.python.org/release/3.12.5/library/dis.html#opcode-RETURN_VALUE
        """
        self.return_value = self.pop()

    def return_const(self, const: tp.Any) -> None:
        self.return_value = const

    def pop_top(self, arg: tp.Any = None) -> None:
        """
        Operation description:
            https://docs.python.org/release/3.12.5/library/dis.html#opcode-POP_TOP
        """
        self.pop()

    def make_function(self, arg: int) -> None:
        """
        Operation description:
            https://docs.python.org/release/3.12.5/library/dis.html#opcode-MAKE_FUNCTION
        """
        if arg & 0x08:
            closure = self.pop()
        if arg & 0x04:
            annotations = self.pop()
        if arg & 0x02:
            kwdefaults = self.pop()
        if arg & 0x01:
            defaults = self.pop()
        code = self.pop()

        
        def f(*args: tp.Any, **kwargs: tp.Any) -> tp.Any:
            parsed_args: dict[str, tp.Any] = {}
            for i in range(code.co_argcount):
                if i < len(args):
                    parsed_args[code.co_varnames[i]] = args[i]
                elif i >= code.co_argcount - len(defaults):
                    parsed_args[code.co_varnames[i]] = defaults[i - (code.co_argcount - len(defaults))]
            parsed_args.update(kwargs)
            f_locals = dict(self.locals)
            f_locals.update(parsed_args)
            frame = Frame(code, self.builtins, self.globals, f_locals)  # Run code in prepared environment
            return frame.run()

        self.push(f)

    def store_name(self, arg: str) -> None:
        """
        Operation description:
            https://docs.python.org/release/3.12.5/library/dis.html#opcode-STORE_NAME
        """
        const = self.pop()
        self.locals[arg] = const

    def store_fast(self, arg: str) -> None:
        const = self.pop()
        self.locals[arg] = const

    def binary_op(self, op:int) -> None:
        right = self.pop()
        left = self.pop()
        if op == 0 or op == 13:
            result = left + right
        elif op == 10 or op == 23:
            result = left - right
        elif op == 5 or op == 18:
            result = left * right
        elif op == 11 or op == 24:
            result = left / right
        elif op == 2 or op == 15:
            result = left // right
        elif op == 6 or op == 19:
            result = left % right
        elif op == 1 or op == 14:
            result = left & right
        elif op == 12 or op == 25:
            result = left ^ right
        elif op == 8 or op == 21:
            result = left ** right
        elif op == 7 or op == 20:
            result = left | right
        elif op == 3 or op == 16:
            result = left << right
        elif op == 9 or op == 22:
            result = left >> right
        else:
            raise NotImplementedError(f"Unknown binary operation: {op}")
        self.push(result)
    def compare_op(self, op: str) -> None:
        right = self.pop()
        left = self.pop()
        if op == "<":
            result = left < right
        elif op == "<=":
            result = left <= right
        elif op == "==":
            result = left == right
        elif op == "!=":
            result = left != right
        elif op == ">":
            result = left > right
        elif op == ">=":
            result = left >= right
        elif op == "in":
            result = left in right
        elif op == "not in":
            result = left not in right
        elif op == "is":
            result = left is right
        elif op == "is not":
            result = left is not right
        elif op == "exception match":
            result = issubclass(left, right)
        elif op == "BAD":
            raise RuntimeError("Bad comparison op")
        else:
            raise NotImplementedError(f"Unknown compare operation: {op}")
        self.push(result)

    ######cycles
    def get_iter(self, _) -> None:
        value = self.pop()
        value = iter(value)
        self.push(value)

    def for_iter(self, argval) -> None:
        iterator = self.peek()
        try:
            value = next(iterator)
            self.push(value)
        except StopIteration:
            self.ind_op = self.offset_to_index[argval]

    def end_for(self, _) -> None:
        self.pop_top()

    def jump_backward(self, argval: int) -> None:
        self.ind_op = self.offset_to_index[argval]

    def jump_forward(self, argval: int) -> None:
        self.ind_op = self.offset_to_index[argval]

    ######

    ##### if
    def pop_jump_if_false(self, argval: int) -> None:
        compare_value = self.pop()
        if not compare_value:
            self.ind_op = self.offset_to_index[argval]
    def pop_jump_is_true(self, argval: int) -> None:
        compare_value = self.pop()
        if compare_value:
            self.ind_op = self.offset_to_index[argval]

    ######

    ###### strings
    def format_value(self, argval: tuple[int | None, bool]) -> None:
        conversion, has_fmt_spec = argval
        if has_fmt_spec:
            fmt_spec = self.pop()
        else:
            fmt_spec = ""

        value = self.pop()
        if conversion is None:
            converted = value
        elif conversion == ord("s"):
            converted = str(value)
        elif conversion == ord("r"):
            converted = repr(value)
        elif conversion == ord("a"):
            converted = ascii(value)
        else:
            raise NotImplementedError(f"Unsupported FORMAT_VALUE conversion: {conversion}")
        self.push(format(converted, fmt_spec))

    def build_string(self, count: int) -> None:
        res = ""
        for i in range(count):
            res = self.pop() + res
        self.push(res)
    def binary_slice(self, _):
        end = self.pop()
        start = self.pop()
        container = self.pop()
        self.push(container[start:end])
    def build_slice(self, argc: int) -> None:
        if argc == 2:
            end = self.pop()
            start = self.pop()
            self.push(slice(start, end))
        elif argc == 3:
            step = self.pop()
            end = self.pop()
            start = self.pop()
            self.push(slice(start, end, step))
    def binary_subscr(self, _) -> None:
        key = self.pop()
        container = self.pop()
        self.push(container[key])
    def store_subscr(self, _: tp.Any) -> None:

        key = self.pop()
        container = self.pop()
        value = self.pop()
        container[key] = value
    def store_slice(self, _) -> None:
        end = self.pop()
        start = self.pop()
        container = self.pop()
        values = self.pop()
        container[start:end] = values
    def delete_subscr(self, _: tp.Any) -> None:
        key = self.pop()
        container = self.pop()
        del container[key]
    def build_tuple(self, count: int) -> None:
        if count == 0:
            value = ()
        else:
            value = tuple(self.data_stack[-count:])
            self.data_stack = self.data_stack[:-count]

        self.push(value)
    def build_list(self, count: int) -> None:
        if count == 0:
            value = []
        else:
            value = list(self.data_stack[-count:])
            self.data_stack = self.data_stack[:-count]
        self.push(value)
    def build_set(self, count: int) -> None:
        if count == 0:
            value = set()
        else:
            value = set(self.data_stack[-count:])
            self.data_stack = self.data_stack[:-count]
        self.push(value)
    def list_extend(self, i:int) -> None:
        seq = self.pop()
        self.data_stack[-i].extend(seq)
    def load_attr(self, namei: int) -> None:
        value = self.pop()
        name = self.code.co_names[namei >> 1]
        if namei & 1:
            try:
                attr = getattr(value, name)
                method = attr.__get__(value, type(value))
                self.push(method)
                self.push(value)
            except AttributeError:
                self.push(None)
                self.push(getattr(value, name))
        else:
            self.push(getattr(value, name))
    def unpack_sequence(self, count: int) -> None:
        assert (len(self.data_stack[-1]) == count)
        self.data_stack.extend(self.pop()[:-count - 1:-1])
    def copy(self, i: int) -> None:
        assert i > 0
        self.push(self.data_stack[-i])
    def swap(self, i: int) -> None:
        self.data_stack[-i], self.data_stack[-1] =self.data_stack[-1], self.data_stack[-i]
    def kw_names(self, consti: tuple[str]) -> None:
        pass
class VirtualMachine:
    def run(self, code_obj: types.CodeType) -> None:
        globals_context: dict[str, tp.Any] = {}
        frame = Frame(code_obj, builtins.globals()['__builtins__'], globals_context, globals_context)
        return frame.run()
