from .BIDSContainer import BIDSContainer
from Management import OptionsVar
from utils import get_object_class
from FileTypes.generic_file import generic_file
from FileTypes.BIDSFile import BIDSFile
from FileTypes.FileInfo import FileInfo
from mne.io import read_raw_kit
from mne.io.constants import FIFF


class KITData(BIDSContainer):
    def __init__(self, id_=None, file=None, settings=dict(), parent=None):
        super(KITData, self).__init__(id_, file, settings, parent)

    def _create_vars(self):
        super(KITData, self)._create_vars()

        # KIT specific variables
        self.dewar_position = OptionsVar(value='supine',
                                         options=["supine", "upright"])
        self.con_map = dict()
        self.is_valid = False

    # !REMOVE?
    def initial_processing(self):
        self.load_data()

    def load_data(self):
        # this will automatically preload the data of any contained files

        files = dict()

        file_ids = self.generate_file_list(self._id,
                                           self.parent.file_treeview)

        # go over the found ids and preload their data.
        for ext, sids in file_ids.items():
            files[ext] = list()
            if len(sids) == 0:
                # In this case the folder doesn't contain all the required
                # files so it also doesn't require being saved.
                self.requires_save = self.contains_required_files = False
            for sid in sids:
                # Check to see if the file has already been preloaded.
                # If so, simply associate it and continue.
                if sid in self.parent.preloaded_data:
                    if ext in files:
                        files[ext].append(self.parent.preloaded_data[sid])
                        if isinstance(self.parent.preloaded_data[sid],
                                      BIDSFile):
                            # container will have already been set
                            self.jobs.append(self.parent.preloaded_data[sid])
                else:
                    item = self.parent.file_treeview.item(sid)
                    # generate the FileInfo subclass object
                    cls_ = get_object_class(ext)
                    if not isinstance(cls_, str):
                        # and only call it if it can be. str types are ignored
                        # (only other return type)
                        if issubclass(cls_, BIDSFile):
                            obj = cls_(sid, item['values'][1],
                                       settings=self.parent.proj_settings,
                                       parent=self.parent)
                        elif issubclass(cls_, FileInfo):
                            obj = cls_(sid, item['values'][1],
                                       parent=self.parent)
                        if isinstance(obj, generic_file):
                            obj.dtype = ext
                        if isinstance(obj, BIDSFile):
                            obj.container = self
                            self.jobs.append(obj)
                        # add the data to the preload data
                        self.parent.preloaded_data[sid] = obj
                        files[ext].append(obj)

        # we'll only check whether the folder is ready to be exported to bids
        # format if it is valid
        if self.contains_required_files:
            # first run the verification on each of the jobs to ensure they
            # have been checked
            for job in self.jobs:
                # this is slightly inefficient, but because _check_bids_ready
                # for BIDSContainers is very efficient it won't matter
                job.validate()

            # apply some values
            # TODO: clean this up a bit...
            """ Project settings """
            try:
                proj_name = self.parent.file_treeview.item(
                    self._id)['text'].split('_')[2]
            except IndexError:
                proj_name = ''
            self.proj_name.set(proj_name)
            # set the settings via the setter.
            try:
                self.settings = self.proj_settings
            except AttributeError:
                # in this case the settings have probably already been set.
                pass

            """ Subject settings """
            try:
                sub_name = self.parent.file_treeview.item(
                    self._id)['text'].split('_')[0]
            except IndexError:
                sub_name = ''
            self.subject_ID.set(sub_name)

            self.validate()

        self.contained_files = files
        self.loaded = True

    def prepare(self):
        super(KITData, self).prepare()
        self._create_raws()
        self.make_specific_data = {
            'electrode': self.contained_files['.elp'][0].file,
            'hsp': self.contained_files['.hsp'][0].file}

    # TODO: fix up 'jobs' stuff
    def _create_raws(self):
        print('creating raws')
        # refresh to avoid adding the con files each time
        self.jobs = []
        for con_file in self.contained_files['.con']:
            # first ensure the data is loaded:
            if con_file.loaded is False:
                con_file.load_data()

            if con_file.is_junk.get() is False:
                # TODO: empty room stuff will be updated
                if con_file.is_empty_room.get():
                    con_file.run.set('emptyroom')
                    con_file.task.set('noise')
                trigger_channels, descriptions = con_file.get_event_data()
                con_file.event_info = dict(
                    zip(descriptions, [int(i) for i in trigger_channels]))
                # change the channel type of any channels that are triggers
                for ch in trigger_channels:
                    i = int(ch) - 1
                    raw.info['chs'][i]['kind'] = FIFF.FIFFV_STIM_CH
                # if none are specified we will get MNE to determine them
                # itself
                if trigger_channels == []:
                    trigger_channels = '>'
                    stim_code = 'binary'
                    slope = '-'
                else:
                    stim_code = 'channel'
                    slope = '+'
                print('trigger channels:', trigger_channels)
                raw = read_raw_kit(
                    con_file.file,
                    # construct a list of the file paths
                    mrk=[mrk_file.file for mrk_file in
                         con_file.hpi],
                    elp=self.contained_files['.elp'][0].file,
                    hsp=self.contained_files['.hsp'][0].file,
                    stim=trigger_channels, stim_code=stim_code,
                    slope=slope)
                bads = con_file.bad_channels()
                # set the bads
                raw.info['bads'] = bads

                # assign the subject data
                try:
                    bday = (int(self.subject_age[2].get()),
                            int(self.subject_age[1].get()),
                            int(self.subject_age[0].get()))
                except ValueError:
                    bday = None
                sex = self.subject_gender.get()
                # map the sex to the data used by the raw info
                sex = {'U': 0, 'M': 1, 'F': 2}.get(sex, 0)
                if raw.info['subject_info'] is None:
                    raw.info['subject_info'] = dict()
                raw.info['subject_info']['birthday'] = bday
                raw.info['subject_info']['sex'] = sex

                # assign the raw to the con_file
                con_file.raw = raw

                con_file.extra_data = {
                    'InstitutionName': con_file.info['Institution name'],
                    'ManufacturersModelName': 'KIT-160',
                    'DewarPosition': self.dewar_position.get(),
                    'Name': self.proj_name.get(),
                    'DeviceSerialNumber': con_file.info['Serial Number']}

            self.jobs.append(con_file)

        return True

    @staticmethod
    def generate_file_list(folder_id, treeview, validate=False):
        """ Generate a list of all KIT related files within the folder 
        
        Parameters
        ----------
        folder_id : int
            The id of the folder in the treeview
        treeview : instance of EnhancedTreeview
            The treeview object in the main GUI object
        validate : bool
            Whether to validate the produced list. If True, whether the folder
            is valid or not is returned. Defaults to False.
        
        Returns:
        dict() if validate == False,
        bool otherwise.
        """
        files = {'.con': [],
                 '.mrk': [],
                 '.elp': [],
                 '.hsp': []}

        # go through the direct children of the folder via the treeview
        for sid in treeview.get_children(folder_id):
            item = treeview.item(sid)
            # check the extension of the file. If it is in the files dict, add
            # the file to the list
            ext = item['values'][0]
            if ext in files:
                files[ext].append(sid)

        if not validate:
            return files
        else:
            for lst in files.values():
                if len(lst) == 0:
                    return False
            return True

    def __getstate__(self):
        data = super(KITData, self).__getstate__()
        data['dwr'] = self.dewar_position.get()

        return data

    def __setstate__(self, state):
        super(KITData, self).__setstate__(state)

        self.dewar_position.set(state.get('dwr', 'supine'))
