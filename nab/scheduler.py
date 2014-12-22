""" Module for the scheduler, that can run functions at certain times. """
import time
import threading
import heapq
from collections import deque
import yaml


class _SchedQueue:

    def __init__(self, name):
        self._set = set()
        self._queue = deque()
        self.name = name

    def _yaml_entry(self, dtime, action, arguments):

        def time_str(dtime):
            try:
                return time.ctime(dtime)
            except TypeError:
                return dtime

        return {"time": dtime, "tstr": time_str(dtime),
                "action": action, "arguments": arguments}

    def to_yaml(self):
        yml = []
        for action, arguments in self._queue:
            yml.append(self._yaml_entry(self.name, action, arguments))
        return yml

    def push(self, dtime, action, arguments):
        if (action, arguments) in self._set:
            return False

        self._queue.append((action, arguments))
        self._set.add((action, arguments))
        return True

    def has_next(self):
        return len(self._queue) > 0

    def pop(self):
        if not self.has_next():
            return None

        task = self._queue.popleft()
        self._set.remove(task)
        return task


class _SchedQueueTimed(_SchedQueue):

    def __init__(self, name):
        self._set = set()
        self._queue = []
        self.name = name

    def to_yaml(self):
        yml = []
        # sort by time
        for dtime, action, arguments in sorted(self._queue,
                                               key=lambda e: e[0]):
            yml.append(self._yaml_entry(dtime, action, arguments))
        return yml

    def push(self, dtime, action, arguments):
        if (action, arguments) in self._set:
            # if entry already present, look it up
            match = None
            for (d_q, act_q, arg_q) in self._queue:
                if (act_q, arg_q) == (action, arguments):
                    match = (d_q, act_q, arg_q)
                    break

            # if match found and new time is SOONER, replace it
            # if new time is later, ignore
            if match is not None and match[0] > dtime:
                self._queue.remove(match)
                heapq.heapify(self._queue)  # rearrange into heap
            else:
                return False

        heapq.heappush(self._queue, (dtime, action, arguments))
        self._set.add((action, arguments))
        return True

    def has_next(self):
        if self._queue:
            # get information about next item
            action_time, action, arguments = self._queue[0]

            # if time for next item, return true
            if time.time() >= action_time:
                return True

        return False

    def pop(self):
        action_time, action, arguments = heapq.heappop(self._queue)
        self._set.remove((action, arguments))
        return action, arguments


class Scheduler:
    """
    A scheduler class that lets you schedule functions.

    Example usage:
    >>> my_scheduler = Scheduler()

    Register a function with the scheduler:
    >>> def func(foo):
    ...     print foo
    ...
    >>> sched_func = my_scheduler.register(func)

    Schedule some events:
    >>> import time
    >>> sched_func('asap', 'Hello World!')
    >>> sched_func('lazy', 'Did I miss anything?')
    >>> sched_func('timed', 3, "Where's everybody gone?")
    >>> my_scheduler.start()
    Hello World!
    Did I miss anything?
    >>> time.sleep(4)
    Where's everybody gone?

    'Schedule-ize' functions with the decorator:
    >>> @my_scheduler
    ... def countdown(n):
    ...     print n
    ...     if n == 0:
    ...         sched_func('asap', 'Lift off!')
    ...     if n > 0:
    ...         countdown('timed', 1, n-1)
    ...

    An event can even schedule additional events:
    >>> countdown('asap', 3)
    >>> time.sleep(4)
    3
    2
    1
    0
    Lift off!
    >>> my_scheduler.stop()

    Events can be scheduled to run 'ASAP', 'lazy' or timed.
    ASAP events occur before any lazy or timed events.
    Lazy events occur before timed events
    Timed events occur after the time specified.

    Events are functions, which must be registered before they can be run.
    To register a function, call scheduler.register(func) or scheduler(func).

    scheduler.register(func) and scheduler(func) will return a
    'schedulable' version of the function whose first argument is the type of
    event ('timed', 'lazy' or 'asap'). If 'timed' is chosen then the next
    argument must be a delay measured in seconds.

    These scheduler functions return straight after scheduling their event,
    so there is no way to wait for completion or return values.

    A scheduler can also decorate functions, making them instantly
    'schedule' functions.

    Event parameters must be hashable. There are additional functions
    encode_arguments and decode_arguments that can be overriden to convert
    arguments into hashable or more concise representations.

    Tasks are run in a single thread, one after the other. This avoids any
    concurrency issues.

    A scheduler can optionally use a file to save and load state automatically.
    Whenever the scheduler is started, it will reload the events from the file.
    In this case, it is very important to register all functions before
    starting the scheduler, as there may be functions in the schedule file
    that will run as soon as the scheduler starts.
    """

    def __init__(self, scheduler_log=None, scheduler_file=None):
        """
        Create a new scheduler.

        >>> Scheduler()
        <nab.scheduler.Scheduler instance at 0x...>

        >>> import logging
        >>> Scheduler(logging.Logger('scheduler'))
        <nab.scheduler.Scheduler instance at 0x...>

        Args:
            scheduler_log (logging.Logger, None):
                Logger for logging scheduling events.
                Leave as default for no logging.
            scheduler_file (str, None):
                Path to a (not necessarily existing) schedule file.
                This file will be used to save and load the state of the
                scheduler. Leave as default for no saving and loading state.
        """
        self._log = scheduler_log
        self._scheduler_file = scheduler_file

        self.queue = _SchedQueueTimed('timed')
        self.queue_asap = _SchedQueue('asap')
        self.queue_lazy = _SchedQueue('lazy')

        self._tasks = {}

        self._qlock = threading.Condition()

        self._last_save = 0.0
        self._save_invalidate = False

        self._stop_flag = True

    def __call__(self, f):
        """ Transform the given function into a scheduled function. """
        return self.register(f)

    def register(self, f):
        """ Transform the given function into a scheduled function. """
        self._tasks[f.__name__] = f

        def inner(sched_type, *args):
            return {
                'timed': self._add_timed,
                'asap': self._add_asap,
                'lazy': self._add_lazy
            }[sched_type](f.__name__, *args)

        return inner

    def start(self):
        """ Start the scheduler in a thread and return. """
        if self._stop_flag:
            # load state when starting scheduler
            if self._scheduler_file is not None:
                try:
                    self.load()
                except (IOError, ValueError):
                    pass
            self._log_debug("Starting")
            self._stop_flag = False
            threading.Thread(target=self._run).start()

    def stop(self):
        """ Tell the scheduler to stop running after the task is complete. """
        self._log_debug("Setting stop flag")
        self._stop_flag = True

    def load(self):
        """ Load scheduler events from the schedule yaml file. """
        with open(self._scheduler_file, 'r') as f:
            yml = yaml.load(f)
            if not yml:
                # yaml file is invalid
                raise ValueError("Schedule file is invalid yaml")

            for entry in yml["queue"]:
                dtime = entry["time"]
                action = entry["action"]
                arguments = self.decode_arguments(entry["arguments"])
                arguments = self.encode_arguments(arguments)
                # yes I did just encode the decoded argument
                # this is to add back in tuples, which are hashable

                if dtime == 'asap':
                    self.queue_asap.push(None, action, arguments)
                elif dtime == 'lazy':
                    self.queue_lazy.push(None, action, arguments)
                else:
                    self.queue.push(dtime, action, arguments)

    def save(self):
        """ Save scheduler events to the schedule yaml file. """
        yaml.safe_dump(self._to_yaml(), open(self._scheduler_file, 'w'))

    def encode_arguments(self, arguments):
        return arguments

    def decode_arguments(self, arguments):
        return arguments

    def _to_yaml(self):
        """ Return a yaml representation of the scheduler. """
        return {
            "queue": (self.queue_asap.to_yaml() +
                      self.queue_lazy.to_yaml() +
                      self.queue.to_yaml())
            }

    def _save_decision(self):
        if self._scheduler_file is None:
            # No file set
            return

        if time.time() - self._last_save > 1.0 and self._save_invalidate:
            self.save()
            self._save_invalidate = False
            self._last_save = time.time()

    def _wait_next(self):
        while not self._stop_flag:
            # acquire queue lock
            with self._qlock:
                # check all queues in order of priority
                for q in [self.queue_asap, self.queue, self.queue_lazy]:
                    if q.has_next():
                        return q.pop()

            # test once every second
            time.sleep(1.0)
            self._save_decision()

        return None

    def _run(self):
        while not self._stop_flag:
            task = self._wait_next()

            # stop flag has been set, so waiting has stopped
            if task is None:
                continue

            action, arguments = task

            self._log_debug("Executing scheduled task %s%s"
                            % (action, tuple(arguments)))

            self._tasks[action](*self.decode_arguments(arguments))
            self._save_invalidate = True
            self._save_decision()

        # save state when stopping scheduler
        if self._scheduler_file is not None:
            self.save()

        self._log_debug("Stopping")

    def _add(self, queue, delay, action, arguments):
        arguments = self.encode_arguments(arguments)

        if delay is None:
            dtime = None
            tstr = ""
        else:
            dtime = time.time() + delay
            tstr = " at %s" % time.ctime(dtime)

        with self._qlock:
            if queue.push(dtime, action, arguments):
                self._log_debug("Scheduling %s%s on %s%s"
                                % (action, tuple(arguments), queue.name, tstr))
                self._save_invalidate = True
                self._save_decision()
            self._qlock.notify()

    def _add_timed(self, action, delay, *arguments):
        """ Add a task to the scheduler which will run after time delay. """
        self._add(self.queue, delay, action, arguments)

    def _add_asap(self, action, *arguments):
        """ Add a task to the scheduler which will run as soon as possible. """
        self._add(self.queue_asap, None, action, arguments)

    def _add_lazy(self, action, *arguments):
        """ Add a task to the scheduler which will run after ASAP tasks. """
        self._add(self.queue_lazy, None, action, arguments)

    def _log_debug(self, message):
        try:
            self._log.debug(message)
        except AttributeError:
            pass


class NabScheduler:

    """ Scheduler for nab that encodes and decodes ShowElems. """

    def __init__(self, scheduler_log, scheduler_file, shows):
        self.super(scheduler_log, scheduler_file)
        self._shows = shows

    def encode_arguments(self, arguments):
        new_arguments = []
        for arg in arguments:
            try:
                # if this is a show tree element, get identifier to save
                arg = ("show_entry", arg.id)
            except AttributeError:
                pass
            new_arguments.append(arg)
        return tuple(new_arguments)

    def decode_arguments(self, arguments):
        new_arguments = []
        for arg in arguments:
            try:
                iter(arg)
            except TypeError:
                pass
            else:
                if arg[0] == "show_entry":
                    # find element matching id
                    narg = self._shows.find(tuple(arg[1]))
                    if narg is None:
                        raise TypeError("No match for entry %s" % arg)
                    arg = narg
            new_arguments.append(arg)
        return tuple(new_arguments)
