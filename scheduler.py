import time
import threading
import log
import heapq
from collections import deque
import yaml

_log = log.log.getChild("scheduler")


# lists all valid scheduler tasks
tasks = {}

_shows = None


def init(shows):
    global _shows
    _shows = shows

    try:
        scheduler.load()
    except IOError:
        pass

    scheduler.start()


class Scheduler:

    def __init__(self):
        self.queue = []
        self.queue_asap = deque()
        self._qlock = threading.Condition()

        self._last_save = 0.0
        self._save_invalidate = False

    def to_yaml(self):
        yml = {"queue": [], "asap": []}

        def yaml_entry(dtime, action, argument):
            return {
                "time": dtime,
                "action": action,
                "argument": self._encode_argument(argument)
            }

        for dtime, action, argument in self.queue:
            yml["queue"].append(yaml_entry(dtime, action, argument))

        for action, argument in self.queue_asap:
            yml["asap"].append(yaml_entry(None, action, argument))

        return yml

    def load(self):
        with file('schedule.yaml', 'r') as f:
                yml = yaml.load(f)

                for entry in yml["queue"]:
                    heapq.heappush(
                        self.queue,
                        (entry["time"], entry["action"],
                         self._decode_argument(entry["argument"])))

                for entry in yml["asap"]:
                    self.queue_asap.append(
                        (entry["action"],
                         self._decode_argument(entry["argument"])))

    def save(self):
        yaml.safe_dump(self.to_yaml(), file('schedule.yaml', 'w'))

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
                if len(self.queue) + len(self.queue_asap) == 0:
                    # save whenever queue is empty
                    self.save()
                    # wait for item to be added
                    self._qlock.wait()

                # check if anything in asap queue
                if self.queue_asap:
                    return self.queue_asap.popleft()

                # get information about next item
                action_time, action, argument = self.queue[0]

                # if time for next item, remove and return it
                if time.time() >= action_time:
                    heapq.heappop(self.queue)
                    return action, argument

            # test once every second
            time.sleep(1.0)
            self._save_decision()

    def _run(self):
        while True:
            action, argument = self._wait_next()
            tasks[action](*argument)
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
        return new_arguments

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
        return new_arguments

    def add(self, delay, action, *argument):
        with self._qlock:
            dtime = time.time() + delay
            _log.debug("Scheduling %s%s at %s"
                       % (action, tuple(argument), time.ctime(dtime)))
            heapq.heappush(self.queue, (dtime, action, argument))
            self._save_invalidate = True
            self._save_decision()
            self._qlock.notify()

    def add_asap(self, action, *argument):
        with self._qlock:
            _log.debug("Scheduling %s%s ASAP" % (action, tuple(argument)))
            self.queue_asap.append((action, argument))
            self._save_invalidate = True
            self._save_decision()
            self._qlock.notify()

    def contains(self, action):
        for (_, entry_action, _) in self.queue:
            if entry_action == action:
                return True

        for (entry_action, _) in self.queue_asap:
            if entry_action == action:
                return True

        return False


scheduler = Scheduler()
