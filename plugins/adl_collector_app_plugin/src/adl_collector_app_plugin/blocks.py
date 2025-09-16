from django.core.exceptions import ValidationError
from wagtail import blocks
from wagtail.blocks import StructBlockValidationError


class FixedSlotLocalScheduleMode(blocks.StructBlock):
    slots = blocks.ListBlock(
        blocks.TimeBlock(help_text="Select a fixed slot time"),
        min_num=1,
        max_num=24,
        help_text="Select one or more fixed slots",
        default=[
            '06:00', '12:00', '18:00', '00:00'
        ],
    )
    window_before_mins = blocks.IntegerBlock(
        default=20, help_text="Minutes before the slot time to start observation"
    )
    window_after_mins = blocks.IntegerBlock(
        default=20, help_text="Minutes after the slot time to end observation"
    )
    grace_late_mins = blocks.IntegerBlock(
        default=60, help_text="Grace period in minutes for late observations"
    )
    rounding_increment_mins = blocks.IntegerBlock(
        default=5, help_text="Rounding increment in minutes for scheduling"
    )
    backfill_days = blocks.IntegerBlock(
        default=2, help_text="Number of days to backfill missed observations"
    )
    allow_future_mins = blocks.IntegerBlock(
        default=2, help_text="Allow scheduling this many minutes into the future"
    )
    cutoff_policy = blocks.ChoiceBlock(
        choices=[
            ('ACCEPT_WITH_LATE_FLAG', 'Accept with late flag'),
            ('REJECT', 'Reject'),
        ],
        default='ACCEPT_WITH_LATE_FLAG',
        help_text="Policy for handling missed observation windows"
    )
    duplicate_policy = blocks.ChoiceBlock(
        choices=[
            ('REVISION_WITH_REASON', 'Create revision with reason'),
            ('REJECT', 'Reject'),
        ],
        default='REVISION_WITH_REASON',
        help_text="Policy for handling duplicate observations"
    )
    lock_after_mins = blocks.IntegerBlock(
        default=1440, help_text="Lock the schedule after this many minutes"
    )
    rain_accumulation_rule = blocks.ChoiceBlock(
        choices=[
            ('RAIN_SINCE_PREV', 'Rain since previous observation'),
        ],
        default='RAIN_SINCE_PREV',
        help_text="Rule for calculating rain accumulation"
    )
    accumulation_obs_day_rollover_local_time = blocks.TimeBlock(
        default='06:00',
        help_text="Local time for daily rollover of accumulation observations"
    )
    
    def clean(self, value):
        result = super().clean(value)
        
        slots = result.get('slots', [])
        
        # Ensure no duplicate slot times
        if len(slots) != len(set(slots)):
            raise StructBlockValidationError(block_errors={
                "slots": ValidationError("Duplicate slot times are not allowed.")
            })
        
        return result


class WindowedOnlyScheduleMode(blocks.StructBlock):
    window_start = blocks.TimeBlock(help_text="Start time of the observation window", default='06:00')
    window_end = blocks.TimeBlock(help_text="End time of the observation window", default='18:00')
    max_submissions_per_window = blocks.IntegerBlock(
        default=1, help_text="Maximum number of submissions allowed per window"
    ),
    grace_late_mins = blocks.IntegerBlock(
        default=45, help_text="Grace period in minutes for late observations"
    )
    rounding_increment_mins = blocks.IntegerBlock(
        default=5, help_text="Rounding increment in minutes for scheduling"
    )
    backfill_days = blocks.IntegerBlock(
        default=2, help_text="Number of days to backfill missed observations"
    )
    allow_future_mins = blocks.IntegerBlock(
        default=2, help_text="Allow scheduling this many minutes into the future"
    )
    cutoff_policy = blocks.ChoiceBlock(
        choices=[
            ('ACCEPT_WITH_LATE_FLAG', 'Accept with late flag'),
            ('REJECT', 'Reject'),
        ],
        default='ACCEPT_WITH_LATE_FLAG',
        help_text="Policy for handling missed observation windows"
    )
    duplicate_policy = blocks.ChoiceBlock(
        choices=[
            ('REVISION_WITH_REASON', 'Create revision with reason'),
            ('REJECT', 'Reject'),
        ],
        default='REVISION_WITH_REASON',
        help_text="Policy for handling duplicate observations"
    )
    lock_after_mins = blocks.IntegerBlock(
        default=1440, help_text="Lock the schedule after this many minutes"
    )
    rain_accumulation_rule = blocks.ChoiceBlock(
        choices=[
            ('RAIN_SINCE_PREV', 'Rain since previous observation'),
            ('RAIN_24H_ENDING_SLOT', 'Rain in the 24 hours ending at the slot time'),
        ],
        default='RAIN_SINCE_PREV',
        help_text="Rule for calculating rain accumulation"
    )
    accumulation_obs_day_rollover_local_time = blocks.TimeBlock(
        default='06:00',
        help_text="Local time for daily rollover of accumulation observations"
    )
    
    def clean(self, value):
        result = super().clean(value)
        window_start = result.get('window_start')
        window_end = result.get('window_end')
        
        if window_start >= window_end:
            raise StructBlockValidationError(block_errors={
                "window_start": ValidationError("window_start must be before window_end."),
                "window_end": ValidationError("window_end must be after window_start."),
            })
        return result
