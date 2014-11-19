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


class Scheduler:

    def __init__(self):
        self.queue = []
        self.queue_asap = deque()
        self.queue_lazy = deque()

        self.queue_set = set()
        self.queue_set_asap = set()
        self.queue_set_lazy = set()

        self._qlock = threading.Condition()

        self._last_save = 0.0
        self._save_invalidate = False

    def to_yaml(self):
        yml = {"queue": []}

        def time_str(dtime):
            try:
                return time.ctime(dtime)
            except TypeError:
                return dtime

        def yaml_entry(dtime, action, argument):
            return {"time": dtime, "tstr": time_str(dtime),
                    "action": action, "argument": argument}

        for action, argument in self.queue_asap:
            yml["queue"].append(yaml_entry('asap', action, argument))

        for dtime, action, argument in sorted(self.queue, key=lambda e: e[0]):
            yml["queue"].append(yaml_entry(dtime, action, argument))

        for action, argument in self.queue_lazy:
            yml["queue"].append(yaml_entry('lazy', action, argument))

        return yml

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
                    self.queue_asap.append((action, argument))
                    self.queue_set_asap.add((action, argument))
                elif dtime == 'lazy':
                    self.queue_lazy.append((action, argument))
                    self.queue_set_lazy.add((action, argument))
                else:
                    heapq.heappush(self.queue, (dtime, action, argument))
                    self.queue_set.add((action, argument))

    def save(self):
        yaml.safe_dump(self.to_yaml(), file(schedule_file, 'w'))

    def _save_decision(self):
        if time.time() - self._last_save > 1.0 and self._save_invalidate:
            self.save()
            self._save_invalidate = False
            self._last_save = time.time()

    def start(self):
        threading.Thread(target=self._run).start()

    def _wait_next(self):
        while True:
            # acquire queue lock
            with self._qlock:
                if (len(self.queue) + len(self.queue_asap) +
                   len(self.queue_lazy)) == 0:
                    # save whenever queue is empty
                    self.save()
                    # wait for item to be added
                    self._qlock.wait()

                # check if anything in asap queue
                if self.queue_asap:
                    task = self.queue_asap.popleft()
                    self.queue_set_asap.remove(task)
                    return task

                # get information about next item
                action_time, action, argument = self.queue[0]

                # if time for next item, remove and return it
                if time.time() >= action_time:
                    heapq.heappop(self.queue)
                    self.queue_set.remove((action, argument))
                    return action, argument

                # finally consider the lazy queue
                if self.queue_lazy:
                    task = self.queue_lazy.popleft()
                    self.queue_set_lazy.remove(task)
                    return task

            # test once every second
            time.sleep(1.0)
            self._save_decision()

    def _run(self):
        while True:
            action, argument = self._wait_next()

            _log.debug("Executing scheduled task %s%s"
                       % (action, tuple(argument)))

            tasks[action](*self._decode_argument(argument))
            self._save_invalidate = True
            self._save_decision()

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

    def add(self, delay, action, *argument):
        argument = self._encode_argument(argument)
        dtime = time.time() + delay

        with self._qlock:

            if (action, argument) in self.queue_set:
                # if entry already present, look it up
                match = None
                for (d_q, act_q, arg_q) in self.queue:
                    if (act_q, arg_q) == (action, argument):
                        match = (d_q, act_q, arg_q)
                        break

                # if match found and new time is SOONER, replace it
                # if new time is later, ignore
                if match is not None and match[0] > dtime:
                    self.queue.remove(match)
                    heapq.heapify(self.queue)  # rearrange into heap
                else:
                    return

            _log.debug("Scheduling %s%s at %s"
                       % (action, tuple(argument), time.ctime(dtime)))
            heapq.heappush(self.queue, (dtime, action, argument))
            self.queue_set.add((action, argument))

            self._save_invalidate = True
            self._save_decision()
            self._qlock.notify()

    def add_asap(self, action, *argument):
        argument = self._encode_argument(argument)

        if (action, argument) in self.queue_set_asap:
            return

        with self._qlock:
            _log.debug("Scheduling %s%s ASAP" % (action, tuple(argument)))
            self.queue_asap.append((action, argument))
            self.queue_set_asap.add((action, argument))

            self._save_invalidate = True
            self._save_decision()
            self._qlock.notify()

    def add_lazy(self, action, *argument):
        argument = self._encode_argument(argument)

        if (action, argument) in self.queue_set_lazy:
            return

        with self._qlock:
            _log.debug("Scheduling %s%s lazy" % (action, tuple(argument)))
            self.queue_lazy.append((action, argument))
            self.queue_set_lazy.add((action, argument))

            self._save_invalidate = True
            self._save_decision()
            self._qlock.notify()


scheduler = Scheduler()
