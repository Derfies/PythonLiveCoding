import sys
import subprocess

import sublime, sublime_plugin


XMIN, YMIN, XMAX, YMAX = list(range(4))
LC_TARGET_VIEW_ID = 'lc_tgtViewId'
LC_TARGET_PYGLET_VIEW_ID = 'lc_tgtPygletViewId'


def find_view( viewId ):
    for window in sublime.windows():
        for view in window.views():
            if view.id() == viewId:
                return view
    return None


class BaseWindowCommand( sublime_plugin.WindowCommand ):

    def fixedSetLayout( self, window, layout):
        #A bug was introduced in Sublime Text 3, sometime before 3053, in that it
        #changes the active group to 0 when the layout is changed. Annoying.
        active_group = window.active_group()
        window.run_command( 'set_layout', layout )
        num_groups = len( layout['cells'] )
        window.focus_group( min( active_group, num_groups - 1 ) )

    def get_layout(self):
        layout = self.window.get_layout()
        cells = layout['cells']
        rows = layout['rows']
        cols = layout['cols']
        return rows, cols, cells


class ResetCommand( BaseWindowCommand ):

    def run( self ):
        rows, cols, cells = self.get_layout()
        self.fixedSetLayout( self.window, {
            'cols': [0, 1], 
            'rows': [0, 1], 
            'cells': [[0, 0, 1, 1]]
        } )
        for view in self.window.views():
            view.settings().erase( LC_TARGET_VIEW_ID )
            view.settings().erase( LC_TARGET_PYGLET_VIEW_ID )


class StartCommand( BaseWindowCommand ):

    def create_pane( self ):
        
        rows, cols, cells = self.get_layout()
        active_idx = self.window.active_group()

        old_cell = cells[active_idx]

        cols.insert( old_cell[XMAX], (cols[old_cell[XMIN]] + cols[old_cell[XMAX]]) / 2 )
        new_cell = [old_cell[XMAX], old_cell[YMIN], old_cell[XMAX] + 1, old_cell[YMAX]]
        cells.append( new_cell )

        self.fixedSetLayout( self.window, {
            'cols': cols, 
            'rows': rows, 
            'cells': cells
        } )

        srcView = self.window.active_view_in_group( active_idx )
        tgtView = self.window.active_view_in_group( len( cells ) - 1 )
        
        return srcView, tgtView

    def run( self ):

        active_group = self.window.active_group()
        srcView = self.window.active_view_in_group( active_group )
        if srcView.settings().has( LC_TARGET_VIEW_ID ):
            msg = 'Already a live coding session for the current view.'
            sublime.message_dialog( msg )
            return
        
        srcView, tgtView = self.create_pane()
        srcView.settings().set( 'word_wrap', False )
        tgtView.settings().set( 'word_wrap', False )
        srcView.settings().set( LC_TARGET_VIEW_ID, tgtView.id() )


class PygletCommand( BaseWindowCommand ):

    def create_pane( self ):
        
        rows, cols, cells = self.get_layout()
        active_idx = self.window.active_group()

        old_cell = cells[active_idx]

        cols.insert( old_cell[XMAX], (cols[old_cell[XMIN]] + cols[old_cell[XMAX]]) / 2 )
        new_cell = [old_cell[XMAX], old_cell[YMIN], old_cell[XMAX] + 1, old_cell[YMAX]]
        cells.append( new_cell )

        self.fixedSetLayout( self.window, {
            'cols': cols, 
            'rows': rows, 
            'cells': cells
        } )

        srcView = self.window.active_view_in_group( active_idx )
        tgtView = self.window.active_view_in_group( len( cells ) - 1 )
        
        return srcView, tgtView



    def run( self ):

        active_group = self.window.active_group()
        srcView = self.window.active_view_in_group( active_group )
        if srcView.settings().has( LC_TARGET_PYGLET_VIEW_ID ):
            msg = 'Already a live coding session for the current view.'
            sublime.message_dialog( msg )
            return
        
        srcView, tgtView = self.create_pane()
        srcView.settings().set( 'word_wrap', False )
        tgtView.settings().set( 'word_wrap', False )
        srcView.settings().set( LC_TARGET_PYGLET_VIEW_ID, tgtView.id() )
 

class TargetViewReplaceCommand( sublime_plugin.TextCommand ):

    def trace_code( self, contents ):

        # Pull location of python exe and code_tracer.py script from user
        # settings.
        settings = sublime.load_settings( 'PythonLiveCoding.sublime-settings' )
        py_path = settings.get( 'python_executable' )
        tracer_path = settings.get( 'code_tracer' )
        args = [
            py_path, 
            tracer_path,
            '-'
        ]

        # Startup info so we don't open a new command prompt.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Launch, pipe in code and return.
        proc = subprocess.Popen( 
            args, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            startupinfo=startupinfo,
            universal_newlines=True
        )
        out, err = proc.communicate( input=contents )
        return out

    def run( self, edit, srcViewId=None ):
        srcView = find_view( srcViewId )
        contents = srcView.substr( sublime.Region( 0, srcView.size() ) )
        code_report = self.trace_code( contents )
        self.view.replace( edit, sublime.Region( 0, self.view.size() ), code_report )
     
 
class SourceViewEventListener( sublime_plugin.ViewEventListener ):

    @classmethod
    def is_applicable( cls, settings ):
        return settings.has( LC_TARGET_VIEW_ID ) or settings.has( LC_TARGET_PYGLET_VIEW_ID )

    def on_modified_async( self ):
        tgtView = find_view( self.view.settings().get( LC_TARGET_VIEW_ID ) )
        if tgtView is not None:
            
            tgtView.run_command( 'target_view_replace', {'srcViewId': self.view.id()} )


        else:
            print( 'her' )
            tgtView = find_view( self.view.settings().get( LC_TARGET_PYGLET_VIEW_ID ) )

            tgtView.add_phantom("test", tgtView.sel()[0], '<img src="file:///C:/Users/Jamie%20Davies/Documents/git/live-py-plugin/plugin/PySrc/screenshot.png">', sublime.LAYOUT_BLOCK )
            #if not tgtView.file_name():
            #ps = sublime.PhantomSet(tgtView, 'minihtml_preview_phantom')
            #content = '<img src="C:/Users/Jamie Davies/Documents/git/live-py-plugin/plugin/PySrc/screenshot.png"></img>'
            #p = sublime.Phantom(sublime.Region(0), content, sublime.LAYOUT_BLOCK)
            #ps.update([p]) 
                #tgtView.open_file( r'C:\Users\Jamie Davies\Documents\git\live-py-plugin\plugin\PySrc\screenshot.png' )
            #tgtView.file_name( r'C:\Users\Jamie Davies\Documents\git\live-py-plugin\plugin\PySrc\screenshot.png' )

            #lse:
            #    tgtView.run_command( 'reopen' )
            #print( 'here' )

        #self.window.open_file(os.path.join(dir_name, settings_name + ".sublime-settings"))

        #/reopen