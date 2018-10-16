from tkinter import StringVar, BooleanVar
from tkinter.ttk import Frame, Label, Separator
from CustomWidgets.InfoEntries import InfoEntry, InfoLabel, InfoCheck, InfoList


class ConFileFrame(Frame):
    def __init__(self, master, default_settings, *args, **kwargs):
        self.master = master
        self.default_settings = default_settings
        super(ConFileFrame, self).__init__(self.master, *args, **kwargs)

        self._file = None
        self.widgets_created = False

        self._create_widgets()

    def _create_widgets(self):
        # Recording info
        Label(self, text="Recording Information:").grid(column=0, row=0,
                                                        columnspan=2)
        Separator(self, orient='horizontal').grid(column=0, row=1,
                                                  columnspan=2, sticky='ew')
        self.institution_info = InfoLabel(self, 'Institution', "None")
        self.institution_info.label.grid(column=0, row=2)
        self.institution_info.value.grid(column=1, row=2)
        self.serial_num_info = InfoLabel(self, 'Serial Number', "None")
        self.serial_num_info.label.grid(column=0, row=3)
        self.serial_num_info.value.grid(column=1, row=3)
        self.channel_info = InfoLabel(self, 'Channels', "None")
        self.channel_info.label.grid(column=0, row=4)
        self.channel_info.value.grid(column=1, row=4)
        self.meas_date_info = InfoLabel(self, 'Measurement date', "None")
        self.meas_date_info.label.grid(column=0, row=5)
        self.meas_date_info.value.grid(column=1, row=5)
        self.gains_info = InfoLabel(self, 'Gains', "None")
        self.gains_info.label.grid(column=0, row=6)
        self.gains_info.value.grid(column=1, row=6)
        self.reTHM_info = InfoLabel(self, 'Has continuous head tracking', 'No')
        self.reTHM_info.label.grid(column=0, row=7)
        self.reTHM_info.value.grid(column=1, row=7)
        Separator(self, orient='horizontal').grid(column=0, row=8,
                                                  columnspan=2, sticky='ew')

        # Required info

        Label(self, text="Required Information:").grid(column=0, row=9,
                                                       columnspan=2)

        self.task_info = InfoEntry(self, 'Task', StringVar(),
                                   bad_values=[''],
                                   validate_cmd=None)
        self.task_info.label.grid(column=0, row=10)
        self.task_info.value.grid(column=1, row=10)
        self.acq_info = InfoEntry(self, 'Acquisition', StringVar(),
                                  bad_values=[''],
                                  validate_cmd=None)
        self.acq_info.label.grid(column=0, row=11)
        self.acq_info.value.grid(column=1, row=11)
        self.mrks_info = InfoList(self, "Associated .mrk's", [],
                                  validate_cmd=None)
        self.mrks_info.label.grid(column=0, row=12)
        self.mrks_info.value.grid(column=1, row=12)
        Separator(self, orient='horizontal').grid(column=0, row=13,
                                                  columnspan=2, sticky='ew')

        # Optional info

        Label(self, text="Optional Information:").grid(column=0, row=14,
                                                       columnspan=2)
        self.is_junk_info = InfoCheck(self, 'Is junk', BooleanVar(),
                                      validate_cmd=None)
        self.is_junk_info.label.grid(column=0, row=15)
        self.is_junk_info.value.grid(column=1, row=15)
        self.is_emptyroom_info = InfoCheck(self, 'Is empty room',
                                           BooleanVar(),
                                           validate_cmd=None)
        self.is_emptyroom_info.label.grid(column=0, row=16)
        self.is_emptyroom_info.value.grid(column=1, row=16)
        self.has_emptyroom_info = InfoCheck(self, 'Has empty room',
                                            BooleanVar())
        self.has_emptyroom_info.label.grid(column=0, row=17)
        self.has_emptyroom_info.value.grid(column=1, row=17)
        self.grid()

    def update_widgets(self):
        self.institution_info.value = self.file.info['Institution name']
        self.serial_num_info.value = self.file.info['Serial Number']
        self.channel_info.value = self.file.info['Channels']
        self.meas_date_info.value = self.file.info['Measurement date']
        self.gains_info.value = self.file.info['gains']
        self.reTHM_info.value = str(self.file.extra_data['chm'])

        self.task_info.value = self.file.task
        self.task_info.validate_cmd = self.file.validate
        self.acq_info.value = self.file.acquisition
        self.acq_info.validate_cmd = self.file.validate
        self.mrks_info.value = self.file.hpi
        self.mrks_info.validate_cmd = self.file.validate
        self.is_junk_info.value = self.file.is_junk
        self.is_junk_info.validate_cmd = self.file.validate
        self.is_emptyroom_info.value = self.file.is_empty_room
        self.is_emptyroom_info.validate_cmd = self.file.validate
        self.has_emptyroom_info.value = self.file.has_empty_room

    @property
    def file(self):
        return self._file

    # !UPDATE
    @file.setter
    def file(self, value):
        self._file = value
        self.update_widgets()
        if not self._file.is_good:
            self.acq_info.check_valid()
            self.task_info.check_valid()
