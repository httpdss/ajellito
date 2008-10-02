from us49 import TestUS49Base
from agilito.models import TaskLog
import datetime
from decimal import Decimal

class TestUS128(TestUS49Base):
    def test_tc77(self):
        """
        When new task is created, estimated time should be copied over
        to time remaining. Team member should see this change happen
        on the screen.
        """
        b = self.browser
        b.open(self.story.get_absolute_url() + 'task/add/')
        b.wait()
        estimate = "3"
        b.type("id_estimate", estimate)
        self.assertEqual(b.get_value("id_remaining"), estimate)

    def test_tc78(self):
        """
        Change the estimate for a task without any actual hours. Time
        remaining should be changed to the new estimate.
        """
        b = self.browser
        b.open(self.task_a.get_absolute_url() + 'edit/')
        b.wait()
        estimate = str(self.task_a.estimate * 3)
        b.type("id_estimate", estimate)
        self.assertEqual(b.get_value("id_remaining"), estimate)

    def test_tc79(self):
        """
        A task that has actual time logged should not have its time
        remaining value changed, even when the estimated time value is
        changed.
        """
        tl = TaskLog(task=self.task_b,
                     time_on_task=5,
                     summary='...',
                     date=datetime.date.today(),
                     iteration=self.iteration,
                     owner=self.user,
                     old_remaining=self.task_b.remaining)
        tl.save()

        b = self.browser
        b.open(self.task_b.get_absolute_url() + 'edit/')
        b.wait()
        estimate = str(self.task_b.estimate * 3)
        b.type("id_estimate", estimate)
        self.assertEqual(Decimal(b.get_value("id_remaining")),
                         Decimal(str(self.task_b.remaining)))

    
