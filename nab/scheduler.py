import time
import threading
import log
import heapq
from collections import deque
import yaml
import appdirs
import os

_log = log.log.getChild("scheduler")


# lists all valid scheduler tasks
tasks = {}

_shows = None


schedule_file = os.path.join(appdirs.user_data_dir('nab'), 'schedule.yaml')


def init(shows):
    global _shows
    _shows = shows

    try:
        scheduler.load()
    except (IOError, ValueError):
        pass

    scheduler.start()


class _SchedQueue:

    def __init__(self, name):
        self._set = set()
        self._queue = deque()
        self.name = name

    def _yaml_entry(self, dtime, action, argument):

        def time_str(dtime):
            try:
                return time.ctime(dtime)
            except TypeError:
                return dtime

        return {"time": dtime, "tstr": time_str(dtime),
                "action": action, "argument": argument}

    def to_yaml(self):
        yml = []
        for action, argument in self._queue:
            yml.append(self._yaml_entry(self.name, action, argument))
        return yml

    def push(self, dtime, action, argument):
        if (action, argument) in self._set:
            return False

        self._queue.append((action, argument))
        self._set.add((action, argument))
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
        for dtime, action, argument in sorted(self._queue, key=lambda e: e[0]):
            yml.append(self._yaml_entry(dtime, action, argument))
        return yml

    def push(self, dtime, action, argument):
        if (action, argument) in self._set:
            # if entry already present, look it up
            match = None
            for (d_q, act_q, arg_q) in self._queue:
                if (act_q, arg_q) == (action, argument):
                    match = (d_q, act_q, arg_q)
                    break

            # if match found and new time is SOONER, replace it
            # if new time is later, ignore
            if match is not None and match[0] > dtime:
                self._queue.remove(match)
                heapq.heapify(self._queue)  # rearrange into heap
            else:
                return False

        heapq.heappush(self._queue, (dtime, action, argument))
        self._set.add((action, argument))
        return True

    def has_next(self):
        if self._queue:
            # get information about next item
            action_time, action, argument = self._queue[0]

            # if time for next item, return true
            if time.time() >= action_time:
                return True

        return False

    def pop(self):
        action_time, action, argument = heapq.heappop(self._queue)
        self._set.remove((action, argument))
        return action, argument


class Scheduler:

    def __init__(self):
        self.queue = _SchedQueueTimed('timed')
        self.queue_asap = _SchedQueue('asap')
        self.queue_lazy = _SchedQueue('lazy')

        self._qlock = threading.Condition()

        self._last_save = 0.0
        self._save_invalidate = False

        self._stop_flag = True

    def to_yaml(self):
        return {
            "queue": (self.queue_asap.to_yaml() +
                      self.queue_lazy.to_yaml() +
                      self.queue.to_yaml())
            }

    def load(self):
        with file(schedule_file, 'r') as f:
            yml = yaml.load(f)
            if not yml:
                # yaml file is invalid
                raise ValueError("Schedule file is invalid yaml")

            for entry in yml["queue"]:
                dtime = entry["time"]
                action = entry["action"]
                argument = self._decode_argument(entry["argument"])
                argument = self._encode_argument(argument)
                # yes I did just encode the decoded argument
                # this is to add back in tuples, which are hashable

                if dtime == 'asap':
                    self.queue_asap.push(None, action, argument)
                elif dtime == 'lazy':
                    self.queue_lazy.push(None, action, argument)
                else:
                    self.queue.push(dtime, action, argument)

    def save(self):
        yaml.safe_dump(self.to_yaml(), file(schedule_file, 'w'))

    def _save_decision(self):
        if time.time() - self._last_save > 1.0 and self._save_invalidate:
            self.save()
            self._save_invalidate = False
            self._last_save = time.time()

    def start(self):
        if self._stop_flag:
            _log.debug("Starting")
            self._stop_flag = False
            threading.Thread(target=self._run).start()

    def stop(self):
        _log.debug("Setting stop flag")
        self._stop_flag = True

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

            action, argument = task

            _log.debug("Executing scheduled task %s%s"
                       % (action, tuple(argument)))

            tasks[action](*self._decode_argument(argument))
            self._save_invalidate = True
            self._save_decision()

        # save state when stopping scheduler
        self.save()

        _log.debug("Stopping")

    def _encode_argument(self, argument):
        new_arguments = []
        for arg in argument:
            try:
                # if this is a show tree element, get identifier to save
                arg = ("show_entry", arg.id)
            except AttributeError:
                pass
            new_arguments.append(arg)
        return tuple(new_arguments)

    def _decode_argument(self, argument):
        new_arguments = []
        for arg in argument:
            try:
                iter(arg)
            except TypeError:
                pass
            else:
                if arg[0] == "show_entry":
                    # find element matching id
                    narg = _shows.find(tuple(arg[1]))
                    if narg is None:
                        raise TypeError("No match for entry %s" % arg)
                    arg = narg
            new_arguments.append(arg)
        return tuple(new_arguments)

    def _add(self, queue, delay, action, argument):
        argument = self._encode_argument(argument)

        if delay is None:
            dtime = None
            tstr = ""
        else:
            dtime = time.time() + delay
            tstr = " at %s" % time.ctime(dtime)

        with self._qlock:
            if queue.push(dtime, action, argument):
                _log.debug("Scheduling %s%s on %s%s"
                           % (action, tuple(argument), queue.name, tstr))
                self._save_invalidate = True
                self._save_decision()
            self._qlock.notify()

    def add(self, delay, action, *argument):
        self._add(self.queue, delay, action, argument)

    def add_asap(self, action, *argument):
        self._add(self.queue_asap, None, action, argument)

    def add_lazy(self, action, *argument):
        self._add(self.queue_lazy, None, action, argument)


scheduler = Scheduler()
