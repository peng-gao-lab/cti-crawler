import threading
import time
from utils.logger import create_logger


class MultiThreadedTaskScheduler():
    def __init__(self, num_threads, fn, logger_prefix, check_num_results=0, \
                thread_join_timeout=None, exception_count_limit=0, tasks=[]):
        self.num_threads = num_threads
        self.fn = fn
        self.tasks = tasks
        self.results = []
        self.check_num_results = check_num_results
        self.threads = []
        self.exception_count = 0
        self.exception_count_limit = exception_count_limit
        self.lock = threading.Lock()
        self.running = False
        self.thread_join_timeout = thread_join_timeout
        self.logger = create_logger('{} - Multithreaded Task Scheduler'.format(logger_prefix))

    # Start the task scheduler
    def start(self):
        self.logger.info("Starting")
        self.running = True

        try:
            self.logger.info("Starting {} threads".format(self.num_threads))
            # Create and start threads
            for _ in range(self.num_threads):
                thread = threading.Thread(target=self.thread_run)
                self.threads.append(thread)
                thread.start()

        except Exception as e:
            self.logger.info("Encountered an error while starting")
            self.logger.exception(e)

    def thread_run(self):
        while self.running:
            args = None
            # if (self.check_num_results > 0):
            #     self.logger.info("Trying to acquire lock to retrieve task")
            self.lock.acquire()
            if self.tasks:
                args = self.tasks.pop()
                if (self.check_num_results > 0):
                    self.logger.info("Popped {} from tasks".format(args))
            # if (self.check_num_results > 0):
            #     self.logger.info("Lock released")
            self.lock.release()

            if args:
                try:
                    result = self.fn(args)
                    self.results.append(result)
                    if (self.check_num_results > 0):
                        self.logger.info("Number of completed tasks is now {}".format(len(self.results)))
                except Exception as e:
                    self.exception_count += 1
                    self.logger.exception(e)

                if self.exception_count > self.exception_count_limit:
                    self.logger.info(
                        "Exceeded exception count limit of {} - Exiting".format(self.exception_count_limit))
                    # Scheduler finishes prematurely if we exceed exception count limit
                    self.running = False
                    self.lock.acquire()
                    self.tasks = []
                    self.lock.release()

    # Add task to tasks queue
    # args could be variable length so need to take into account
    def add_task(self, args):
        self.lock.acquire()
        self.tasks.append(args)
        self.lock.release()

    def add_function(self, fn):
        self.fn = fn

    def get_results(self):
        return self.results

    # Wait until execution of all tasks in the task scheduler are complete
    def wait(self):
        self.logger.info("Waiting for all tasks to complete")

        # wait until tasks queue is empty or if we want to check results, ensure we have the correct number
        while self.tasks or (self.check_num_results > 0 and self.check_num_results != len(self.results)):
            # busy waiting
            time.sleep(1)

        self.running = False

        # Wait for all threads to finish running giving each one a timeout if necessary
        for thread in self.threads:
            thread.join(self.thread_join_timeout)

        self.logger.info("All tasks complete - exiting")

        return
