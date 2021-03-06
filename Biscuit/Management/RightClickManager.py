from tkinter import Menu, StringVar, messagebox, simpledialog, filedialog
import os.path as path
import re

from bidshandler import BIDSTree, Project, Subject, Session

from Biscuit.FileTypes import con_file, Folder, BIDSContainer
from Biscuit.utils.utils import create_folder, assign_bids_folder
from Biscuit.Windows.SendFilesWindow import SendFilesWindow
from Biscuit.utils.authorise import authorise
from Biscuit.utils.utils import validate_markers


# pattern to match with folder names to determine if the folder is the result
# of the export process.
# This is to allow the right-click context to upload the data to the archive.
BIDS_PATTERN = re.compile("BIDS-[0-9]{4}-[0-9]{2}")


class RightClick():
    def __init__(self, parent, context):
        self.parent = parent

        # create a popup menu
        self.popup_menu = Menu(self.parent, tearoff=0)

        self.prev_selection = ()
        self.curr_selection = ()

        self.progress = StringVar()
        self.progress.set('None')

        self.context = context

        self.cached_selection = None

#region public methods

    def popup(self, event):
        self._add_options()
        self.popup_menu.post(event.x_root, event.y_root)

    def set_current_selected(self):
        # keep track of the files selected each time a right-click occurs
        if self.prev_selection != self.curr_selection:
            # assign the previous set of selected files if they have changed
            self.prev_selection = self.curr_selection
        # now get the current set of selected files
        self.curr_selection = self.parent.file_treeview.selection()

    def undraw(self, event):
        self.popup_menu.unpost()

#region private methods

    def _add_options(self):
        # a context dependent function to only add options that are applicable
        # to the current situation.
        # first, remove any currently visible entries in the menu so we can
        # draw only the ones required by the current context
        self.popup_menu.delete(0, self.popup_menu.index("end"))
        # now, draw the manu elements required depending on context
        if self.parent.treeview_select_mode == "NORMAL":
            # add an option to associate the file as extra data to be included
            # in the bids output
            self.popup_menu.add_command(label="Add to BIDS output",
                                        command=self._add_to_bids)
            if ('.CON' in self.context or '.MRK' in self.context):
                self.popup_menu.add_command(label="Associate",
                                            command=self._associate_mrk)
            else:
                pass

        elif self.parent.treeview_select_mode.startswith("ASSOCIATE"):
            if (('.MRK' in self.context and
                 self.parent.treeview_select_mode == 'ASSOCIATE-MRK') or
                    ('.CON' in self.context and
                     self.parent.treeview_select_mode == 'ASSOCIATE-CON')):
                self.popup_menu.add_command(label="Associate",
                                            command=self._associate_mrk)

        # give the option to associate one or more mrk files with all con files
        if (".MRK" in self.context and
                not self.parent.treeview_select_mode.startswith("ASSOCIATE")):
            self.popup_menu.add_command(
                label="Associate with all",
                command=lambda: self._associate_mrk(all_=True))
        # Add an option mark all selected .con files as junk
        if ".CON" in self.context and not self.context.is_mixed:
            self.popup_menu.add_command(label="Ignore file(s)",
                                        command=self._ignore_cons)
            self.popup_menu.add_command(label="Include file(s)",
                                        command=self._include_cons)
        if len(self.curr_selection) == 1:
            fname = self.parent.file_treeview.get_text(self.curr_selection[0])
            fpath = self.parent.file_treeview.get_filepath(
                self.curr_selection[0])
            # the selected object
            selected_obj = self.parent.preloaded_data[self.curr_selection[0]]
            # if the folder is a BIDS folder allow it to be uploaded to the
            # archive
            if BIDS_PATTERN.match(fname):
                self.popup_menu.add_command(
                    label="Upload to archive",
                    command=lambda: self._upload())
            # allow any folder to be sent to another location using the
            # BIDSMERGE functionality
            if isinstance(selected_obj,
                          (BIDSTree, Project, Subject, Session)):
                self.popup_menu.add_command(
                    label="Send to...",
                    command=lambda: self._send_to())
            if path.isdir(fpath):
                if isinstance(self.parent.preloaded_data.get(
                        self.curr_selection[0], None), Folder):
                    self.popup_menu.add_command(
                        label="Assign as BIDS folder",
                        command=self._toggle_bids_folder)

    def _add_to_bids(self):
        """Add the selected file(s) to the list of files to be retained across
        BIDS conversion.
        """
        sids = self.curr_selection
        parent_obj = None
        for sid in sids:
            parent = self.parent.file_treeview.parent(sid)
            fpath = self.parent.file_treeview.get_filepath(sid)
            parent_obj = self.parent.preloaded_data.get(parent, None)
            if isinstance(parent_obj, BIDSContainer):
                parent_obj.extra_files.append(fpath)

    def _associate_mrk(self, all_=False):
        """
        Allow the user to select an .mrk file if a .con file has been
        selected (or vice-versa) and associate the mrk file with the con file.
        """
        # First do a simple check for a mixed selection.
        if self.context.is_mixed:
            cont = messagebox.askretrycancel(
                "Error",
                ("You have not selected only .mrk or only .con files. Please "
                 "select a single file type at a time or press 'cancel' to "
                 "stop associating."))
            if not cont:
                self.parent.treeview_select_mode = "NORMAL"
            self.curr_selection = self.prev_selection
            return

        mrk_files = None
        con_files = None
        issue = False
        cont = True
        # Set the current selection to the appropriate type
        if '.MRK' in self.context:
            mrk_files = [self.parent.preloaded_data[sid] for
                         sid in self.curr_selection]
        elif '.CON' in self.context:
            con_files = [self.parent.preloaded_data[sid] for
                         sid in self.curr_selection]
        else:
            # TODO: improve message/dialog
            messagebox.showerror("Error", "Invalid file selection")
            self.curr_selection = self.prev_selection
            return

        # Associate selected mrk files with all other con files in folder.
        if all_:
            # This can only be called if we have mrk files selected.
            # Get the parent folder and then find all .con file children.
            parent = self.parent.file_treeview.parent(mrk_files[0].ID)
            container = self.parent.preloaded_data[parent]
            for con in container.contained_files['.con']:
                con.hpi = mrk_files
                con.validate()
            return

        if self.parent.treeview_select_mode == "NORMAL":
            # Change the treeview mode and display a message if needed.
            if '.MRK' in self.context:
                # Make sure the markers are in the same folder and there aren't
                # too many.
                issue, cont = validate_markers(self.parent.file_treeview,
                                               mrk_files)
                if not issue:
                    self.parent.set_treeview_mode("ASSOCIATE-CON")
                    self.cached_selection = mrk_files
            elif '.CON' in self.context:
                self.parent.set_treeview_mode("ASSOCIATE-MRK")
                self.cached_selection = con_files
            # Finish up if there is no issue. If there is we want to handle it
            # correctly later.
            if not issue:
                if self.parent.settings.get('SHOW_ASSOC_MESSAGE', True):
                    msg = ("Please select the {0} file(s) associated with "
                           "this file.\nOnce you have selected all required "
                           "files, right click and press 'associate' again")
                    # getting the context from the variable is a bit hacky...
                    ctx = list(self.context.get())[0].lower()
                    new_ctx = {'.con': '.mrk', '.mrk': '.con'}.get(ctx)
                    messagebox.showinfo("Select", msg.format(new_ctx))
                return

        # make sure the marker files and con files are in the same location
        elif self.parent.treeview_select_mode == "ASSOCIATE-MRK":
            con_files = self.cached_selection
            issue, cont = validate_markers(self.parent.file_treeview,
                                           mrk_files, con_files)
        elif self.parent.treeview_select_mode == "ASSOCIATE-CON":
            mrk_files = self.cached_selection
            issue, cont = validate_markers(self.parent.file_treeview,
                                           mrk_files, con_files)

        # Handle any issues/check for continuation.
        if issue:
            if not cont:
                self.parent.set_treeview_mode("NORMAL")
            self.curr_selection = self.prev_selection
            return

        if self.parent.treeview_select_mode.startswith('ASSOCIATE'):
            # Now associate the mrk files with the con files:
            for cf in con_files:
                cf.hpi = mrk_files
                cf.validate()
            # Check if the con file is the currently selected file.
            if self.parent.treeview_select_mode == "ASSOCIATE-CON":
                # if so, redraw the info panel and call the mrk
                # association function so GUI is updated
                self.parent.info_notebook.determine_tabs()
                self.parent.highlight_associated_mrks(None)
            self.parent.set_treeview_mode("NORMAL")
            self.cached_selection = None

    def _create_folder(self):
        """
        Create a folder at the currently open level. Clicking on a folder and
        selecting "create folder" will create a sibling folder, not child
        folder (not sure which to do?)
        """
        # get the current root depth
        if self.context != set():        # maybe??
            dir_ = path.dirname(
                self.parent.file_treeview.get_filepath(self.curr_selection[0]))
        else:
            dir_ = self.parent.settings['DATA_PATH']
        # ask the user for the folder name:
        folder_name = simpledialog.askstring("Folder Name",
                                             "Enter a folder Name:",
                                             parent=self.parent)
        # we will need to make sure the folder doesn't already exist at the
        # selected level
        if folder_name is not None:
            # create the folder
            full_path = path.join(dir_, folder_name)
            _, exists_already = create_folder(full_path)
            if not exists_already:
                try:
                    parent = self.parent.file_treeview.parent(
                        self.parent.selected_files[0])
                except IndexError:
                    # we have clicked outside the tree. Set the parent as the
                    # root
                    parent = ''
                self.parent.file_treeview.ordered_insert(
                    parent, values=['', str(full_path)], text=folder_name,
                    open=False)
                print('folder created!!')
            else:
                print('Folder already exists!')

    def _ignore_cons(self):
        """
        Set all selected con files to have 'Is Junk' as True
        """
        for sid in self.curr_selection:
            con = self.parent.preloaded_data.get(sid, None)
            if con is not None:
                if isinstance(con, con_file):
                    con.is_junk.set(True)
                    con.validate()

    def _include_cons(self):
        """
        Set all selected con files to have 'Is Junk' as False
        """
        for sid in self.curr_selection:
            con = self.parent.preloaded_data.get(sid, None)
            if con is not None:
                if isinstance(con, con_file):
                    con.is_junk.set(False)
                    con.validate()

    def _send_to(self):
        """Send the selected object to another selected location."""
        src_obj = self.parent.preloaded_data[self.curr_selection[0]]
        dst = filedialog.askdirectory(title="Select BIDS folder")
        if dst != '':
            if isinstance(src_obj, (BIDSTree, Project, Subject, Session)):
                SendFilesWindow(self.parent, src_obj, dst, opt_verify=True)
            else:
                # try and convert the object to a BIDSTree
                try:
                    self._toggle_bids_folder()
                    src_obj = self.parent.preloaded_data[
                        self.curr_selection[0]]
                except TypeError:
                    return

    def _toggle_bids_folder(self):
        """Assign the selected folder as a BIDS-formatted folder.

        This will attempt to load the selected folder into a
        BIDSController.BIDSTree object. If this isn't possible an error will be
        raised stating this.
        """
        sid = self.curr_selection[0]
        fpath = self.parent.file_treeview.get_filepath(sid)

        bids_folder = assign_bids_folder(fpath, self.parent.file_treeview,
                                         self.parent.preloaded_data)
        if bids_folder is not None:
            # Only needed if the current selection is the same thing that has
            # been right-clicked.
            self.parent.info_notebook.data = [bids_folder]
        else:
            messagebox.showerror(
                "Error",
                "Invalid folder selected. Please select a folder which "
                "contains the BIDS project folders.")
            raise TypeError

    def _upload(self):
        """Upload the selected object to the MEG_RAW archive."""
        src_obj = self.parent.preloaded_data[self.curr_selection[0]]
        dst = self.parent.settings.get("ARCHIVE_PATH", None)
        if dst is None:
            messagebox.showerror("No path set!",
                                 "No Archive path has been set. Please set "
                                 "one in the settings.")
            return
        if not isinstance(src_obj, BIDSTree):
            # automatically convert to a BIDSTree object
            try:
                self._toggle_bids_folder()
                src_obj = self.parent.preloaded_data[self.curr_selection[0]]
            except TypeError:
                return

        access = authorise(dst)
        if not access:
            messagebox.showerror("Error",
                                 "Invalid username or password. Please try "
                                 "again.")
            return

        SendFilesWindow(self.parent, src_obj, dst, set_copied=True)
