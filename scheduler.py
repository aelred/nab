import time
import threading
import log
import heapq
from collections import deque

_log = log.log.getChild("scheduler")


class Scheduler:

    def __init__(self):
        self.queue = []
        self.queue_asap = deque()
        self._qlock = threading.Condition()

        threading.Thread(target=self._run).start()

    def _wait_next(self):
        while True:
            # acquire queue lock
            with self._qlock:
                if len(self.queue) + len(self.queue_asap) == 0:
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

    def _run(self):
        while True:
            action, argument = self._wait_next()
            action(*argument)

    def add(self, delay, action, *argument):
        with self._qlock:
            dtime = time.time() + delay
            _log.debug("Scheduling %s%s at %s"
                       % (action.__name__, tuple(argument), time.ctime(dtime)))
            heapq.heappush(self.queue, (dtime, action, argument))
            self._qlock.notify()

    def add_asap(self, action, *argument):
        with self._qlock:
            _log.debug("Scheduling %s%s ASAP"
                       % (action.__name__, tuple(argument)))
            self.queue_asap.append((action, argument))
            self._qlock.notify()


scheduler = Scheduler()
