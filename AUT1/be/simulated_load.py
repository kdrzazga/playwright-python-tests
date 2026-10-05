import contextlib
import functools
import random
import threading
import time


class NoSimulatedLoad:
    def simulate_load_for_call(self, touches_reference_data):
        return contextlib.nullcontext()


class RandomReferenceDataLoad:
    def __init__(
        self,
        delay_probability=0.15,
        delay_rolls_per_operation=3,
        minimum_delay_seconds=2.0,
        maximum_delay_seconds=5.0,
        random_generator=None,
        sleep_function=time.sleep,
        delay_reporter=None,
    ):
        self.delay_probability = delay_probability
        self.delay_rolls_per_operation = delay_rolls_per_operation
        self.minimum_delay_seconds = minimum_delay_seconds
        self.maximum_delay_seconds = maximum_delay_seconds
        self.random_generator = random_generator or random.Random()
        self.sleep_function = sleep_function
        self.delay_reporter = delay_reporter or self._print_delay_message_immediately
        self._state_of_current_thread = threading.local()

    @contextlib.contextmanager
    def simulate_load_for_call(self, touches_reference_data):
        call_state = self._state_of_current_thread
        is_outermost_call = getattr(call_state, "nesting_depth", 0) == 0
        if is_outermost_call:
            call_state.reference_data_touched = False
        call_state.nesting_depth = getattr(call_state, "nesting_depth", 0) + 1
        call_state.reference_data_touched = call_state.reference_data_touched or touches_reference_data
        try:
            yield
        finally:
            call_state.nesting_depth -= 1
            if is_outermost_call and call_state.reference_data_touched:
                self._roll_for_delay_repeatedly()

    @staticmethod
    def _print_delay_message_immediately(message):
        print(message, flush=True)

    def _roll_for_delay_repeatedly(self):
        for roll_number in range(1, self.delay_rolls_per_operation + 1):
            self._delay_with_configured_probability(roll_number)

    def _delay_with_configured_probability(self, roll_number):
        if self.random_generator.random() >= self.delay_probability:
            return
        delay_seconds = self.random_generator.uniform(self.minimum_delay_seconds, self.maximum_delay_seconds)
        self.delay_reporter(
            f"[extra-load] roll {roll_number}/{self.delay_rolls_per_operation}: "
            f"delaying reference data reply by {delay_seconds:.1f} s"
        )
        self.sleep_function(delay_seconds)


def subject_to_simulated_load(method=None, *, touches_reference_data=None):
    def decorate(undecorated_method):
        @functools.wraps(undecorated_method)
        def run_with_simulated_load(self, *arguments, **keyword_arguments):
            method_touches_reference_data = (
                touches_reference_data
                if touches_reference_data is not None
                else getattr(self, "touches_reference_data", False)
            )
            with self.simulated_load.simulate_load_for_call(method_touches_reference_data):
                return undecorated_method(self, *arguments, **keyword_arguments)

        return run_with_simulated_load

    return decorate(method) if method is not None else decorate
