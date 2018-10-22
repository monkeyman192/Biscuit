from .FileInfo import FileInfo
from tkinter import StringVar, BooleanVar


class BIDSFile(FileInfo):
    def __init__(self, id_=None, file=None, settings=dict(), parent=None):
        super(BIDSFile, self).__init__(id_, file, parent)

        self._settings = settings

        self._create_vars()

        if 'emptyroom' in self.file:
            self.is_empty_room.set(True)

    def _create_vars(self):
        FileInfo._create_vars(self)
        self.run = StringVar()
        self.task = StringVar()
        self.is_junk = BooleanVar()
        self.is_empty_room = BooleanVar()
        self.has_empty_room = BooleanVar()

        self.hpi = []

        self.loaded = False

        self.extra_data = dict()

        # event info: a list of lists. The sub-lists contains the event number
        # and the event description
        self.event_info = list()
        # channel info: key - channel name (?), value - something
        self.channel_info = dict()

        self.raw = None
        self.container = None

        # Set all BIDS files to be saved by default
        self.requires_save = True

    def load_data(self):
        pass

    def check_valid(self):
        """
        Go over all the required settings and determine whether the file is
        ready to be exported to the bids format
        """
        is_valid = super(BIDSFile, self).check_valid()
        # if empty room or junk we consider them good
        if self.is_empty_room.get() or self.is_junk.get():
            return is_valid
        is_valid &= self.task.get() != ''
        is_valid &= self.run.get() != ''
        is_valid &= (self.hpi != [])
        return is_valid

    def get_event_data(self):
        return ['', '']

    def post_validate(self):
        if self.container is not None:
            self.container.check_bids_ready()

    def __getstate__(self):
        data = super(BIDSFile, self).__getstate__()

        data['run'] = self.run.get()        # run
        data['tsk'] = self.task.get()               # task
        data['hpi'] = []
        for hpi in self.hpi:
            data['hpi'].append(hpi.file)                 # marker coils
        data['ier'] = self.is_empty_room.get()      # is empty room data?
        data['her'] = self.has_empty_room.get()     # has empty room data?

        return data

    def __setstate__(self, state):
        super(BIDSFile, self).__setstate__(state)
        self.run.set(state.get('run', 0))
        self.task.set(state.get('tsk', ''))
        # these will be just the file paths for now
        for hpi in state.get('hpi', []):
            self.hpi.append(hpi)
        self.is_empty_room.set(state.get('ier', False))
        self.has_empty_room.set(state.get('her', False))
