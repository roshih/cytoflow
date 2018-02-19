#!/usr/bin/env python3.4
# coding: latin-1

# (c) Massachusetts Institute of Technology 2015-2017
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Created on Mar 15, 2015

@author: brian
"""

import os

from pyface.qt import QtGui

from traits.api import (Interface, Str, HasTraits, Instance, Event,
                        List, Property, on_trait_change, HTML, Any, Bool,
                        Tuple, Enum)
from traitsui.api import View, Item, Handler, HGroup, TextEditor, InstanceEditor, TupleEditor, VGroup

import cytoflow.utility as util

from cytoflowgui.subset import ISubset
from cytoflowgui.workflow import Changed
from cytoflowgui.workflow_item import WorkflowItem
from cytoflowgui.flow_task_pane import TabListEditor
from cytoflowgui.serialization import camel_registry

VIEW_PLUGIN_EXT = 'edu.mit.synbio.cytoflow.view_plugins'

class IViewPlugin(Interface):
    """
    
    Attributes
    ----------
    
    id : Str
        The envisage ID used to refer to this plugin
        
    view_id : Str
        Same as the "id" attribute of the IView this plugin wraps
        Prefix: edu.mit.synbio.cytoflowgui.view
        
    short_name : Str
        The view's "short" name - for menus, toolbar tips, etc.
    """
    
    view_id = Str
    short_name = Str

    def get_view(self):
        """Return an IView instance that this plugin wraps"""
        
    
    def get_icon(self):
        """
        Returns an icon for this plugin
        """
class PluginHelpMixin(HasTraits):
    
    _cached_help = HTML
    
    def get_help(self):
        if self._cached_help == "":
            current_dir = os.path.abspath(__file__)
            help_dir = os.path.split(current_dir)[0]
            help_dir = os.path.split(help_dir)[0]
            help_dir = os.path.join(help_dir, "help")
             
            view = self.get_view()
            help_file = None
            for klass in view.__class__.__mro__:
                mod = klass.__module__
                mod_html = mod + ".html"
                 
                h = os.path.join(help_dir, mod_html)
                if os.path.exists(h):
                    help_file = h
                    break
                 
            with open(help_file, encoding = 'utf-8') as f:
                self._cached_help = f.read()
                 
        return self._cached_help
    
class PlotParams(HasTraits):
    title = Str
    xlabel = Str
    ylabel = Str
    huelabel = Str
    
    xlim = Tuple(util.FloatOrNone(""), util.FloatOrNone(""))
    ylim = Tuple(util.FloatOrNone(""), util.FloatOrNone(""))
    col_wrap = util.PositiveInt("", allow_zero = False, allow_none = True)

    sns_style = Enum(['whitegrid', 'darkgrid', 'white', 'dark', 'ticks'])
    sns_context = Enum(['talk', 'poster', 'notebook', 'paper'])

    legend = Bool(True)
    sharex = Bool(True)
    sharey = Bool(True)
    despine = Bool(True)
    
    def default_traits_view(self):
        return View(
                    Item('title',
                         editor = TextEditor(auto_set = False)),
                    Item('xlabel',
                         label = "X label",
                         editor = TextEditor(auto_set = False)),
                    Item('ylabel',
                         label = "Y label",
                         editor = TextEditor(auto_set = False)),
                    Item('huelabel',
                         label = "Hue label",
                         editor = TextEditor(auto_set = False)),
                    VGroup(
                        Item('xlim',
                             editor = TupleEditor(labels = ["Min X", "Max X"],
                                                  editors = [TextEditor(auto_set = False,
                                                                        evaluate = float),
                                                             TextEditor(auto_set = False,
                                                                        evaluate = float)])),
                        Item('ylim',
                             editor = TupleEditor(labels = ["Min Y", "Max Y"],
                                                  editors = [TextEditor(auto_set = False,
                                                                        evaluate = float),
                                                             TextEditor(auto_set = False,
                                                                        evaluate = float)])),
                    show_labels = False),
                    Item('col_wrap',
                         label = "Columns",
                         editor = TextEditor(auto_set = False,
                                             evaluate = int)),
                    Item('sns_style',
                         label = "Style"),
                    Item('sns_context',
                         label = "Context"),
                    Item('legend'),
                    Item('sharex',
                         label = "Share\nX axis?"),
                    Item('sharey',
                         label = "Share\nY axis?"),
                    Item('despine',
                         label = "Despine?"))
        
@camel_registry.dumper(PlotParams, 'plot-params', version = 1)
def _dump_plot_params(params):
    return dict(title = params.title,
                xlabel = params.xlabel,
                ylabel = params.ylabel,
                huelabel = params.huelabel,
                legend = params.legend,
                sharex = params.sharex,
                sharey = params.sharey,
                xlim = params.xlim,
                ylim = params.ylim,
                col_wrap = params.col_wrap)

@camel_registry.loader('plot-params', version = 1)
def _load_plot_params(data, version):
    return PlotParams(**data)
        
class EmptyPlotParams(HasTraits):
    
    def default_traits_view(self):
        return View()
    
@camel_registry.dumper(EmptyPlotParams, 'empty-plot-params', version = 1)
def _dump_empty_plot_params(params):
    return dict()

@camel_registry.loader('empty-plot-params', version = 1)
def _load_empty_plot_params(data, version):
    return EmptyPlotParams()

                        
class PluginViewMixin(HasTraits):
    handler = Instance(Handler, transient = True)    
    
    # transmit some change back to the workflow
    changed = Event
    
    # plot names
    plot_names = List(Any, status = True)
    plot_names_by = Str(status = True)
    current_plot = Any
    
    # kwargs to pass to plot()
    plot_params = Instance(PlotParams, ())
    
    subset_list = List(ISubset)
    subset = Property(Str, depends_on = "subset_list.str")
        
    # MAGIC - returns the value of the "subset" Property, above
    def _get_subset(self):
        return " and ".join([subset.str for subset in self.subset_list if subset.str])
 
    @on_trait_change('subset_list.str')
    def _subset_changed(self, obj, name, old, new):
        self.changed = (Changed.VIEW, (self, 'subset_list', self.subset_list))  
        
    @on_trait_change('plot_params.+', post_init = True)
    def _plot_params_changed(self, obj, name, old, new):
        self.changed = (Changed.VIEW, (self, 'plot_params', self.plot_params))
            
    def should_plot(self, changed, payload):
        """
        Should the owning WorkflowItem refresh the plot when certain things
        change?  `changed` can be:
         - Changed.VIEW -- the view's parameters changed
         - Changed.RESULT -- this WorkflowItem's result changed
         - Changed.PREV_RESULT -- the previous WorkflowItem's result changed
         - Changed.ESTIMATE_RESULT -- the results of calling "estimate" changed
        """
        return True
    
    def plot_wi(self, wi):
        if self.plot_names:
            self.plot(wi.result, 
                      plot_name = self.current_plot,
                      **self.plot_params.trait_get())
        else:
            self.plot(wi.result,
                      **self.plot_params.trait_get())
            
    def enum_plots_wi(self, wi):
        try:
            return self.enum_plots(wi.result)
        except:
            return []
            
    def update_plot_names(self, wi):
        try:
            plot_iter = self.enum_plots_wi(wi)
            plot_names = [x for x in plot_iter]
            if plot_names == [None] or plot_names == []:
                self.plot_names = []
                self.plot_names_by = []
            else:
                self.plot_names = plot_names
                try:
                    self.plot_names_by = ", ".join(plot_iter.by)
                except Exception:
                    self.plot_names_by = ""
                    
                if self.current_plot == None:
                    self.current_plot = self.plot_names[0]
                    
        except Exception:
            self.current_plot = None
            self.plot_names = []

    
    def get_notebook_code(self, idx):
        raise NotImplementedError("get_notebook_code is unimplemented for {id}"
                                  .format(id = self.id))
        

class ViewHandlerMixin(HasTraits):
    """
    Useful bits for view handlers. 
    """
    
    # the view for the current plot
    current_plot_view = \
        View(
            HGroup(
                Item('plot_names_by',
                     editor = TextEditor(),
                     style = "readonly",
                     show_label = False),
                Item('current_plot',
                     editor = TabListEditor(name = 'plot_names'),
                     style = 'custom',
                     show_label = False)))
        
    plot_params_traits = View(Item('plot_params',
                                   editor = InstanceEditor(),
                                   style = 'custom',
                                   show_label = False))
    
    context = Instance(WorkflowItem)
    
    conditions_names = Property(depends_on = "context.conditions")
    previous_conditions_names = Property(depends_on = "context.previous_wi.conditions")
    statistics_names = Property(depends_on = "context.statistics")
    numeric_statistics_names = Property(depends_on = "context.statistics")
    
    # MAGIC: gets value for property "conditions_names"
    def _get_conditions_names(self):
        if self.context and self.context.conditions:
            return list(self.context.conditions.keys())
        else:
            return []
    
    # MAGIC: gets value for property "previous_conditions_names"
    def _get_previous_conditions_names(self):
        if self.context and self.context.previous_wi and self.context.previous_wi.conditions:
            return list(self.context.previous_wi.conditions.keys())
        else:
            return []
        
    # MAGIC: gets value for property "statistics_names"
    def _get_statistics_names(self):
        if self.context and self.context.statistics:
            return list(self.context.statistics.keys())
        else:
            return []

    # MAGIC: gets value for property "numeric_statistics_names"
    def _get_numeric_statistics_names(self):
        if self.context and self.context.statistics:
            return [x for x in list(self.context.statistics.keys())
                            if util.is_numeric(self.context.statistics[x])]
        else:
            return []

    @on_trait_change('context.view_error_trait', 
                     dispatch = 'ui', 
                     post_init = True)
    def _view_trait_error(self):
        
        # check if we're getting called on the local or remote process
        if self.info is None or self.info.ui is None:
            return
        
        for ed in self.info.ui._editors:  
                          
            if ed.name == self.context.view_error_trait:
                err_state = True
            else:
                err_state = False

            if not ed.label_control:
                continue
            
            item = ed.label_control
            
            if not err_state and not hasattr(item, '_ok_color'):
                continue
            
            pal = QtGui.QPalette(item.palette())  # @UndefinedVariable
            
            if err_state:
                setattr(item, 
                        '_ok_color', 
                        QtGui.QColor(pal.color(item.backgroundRole())))  # @UndefinedVariable
                pal.setColor(item.backgroundRole(), QtGui.QColor(255, 145, 145))  # @UndefinedVariable
                item.setAutoFillBackground(True)
                item.setPalette(pal)
            else:
                pal.setColor(item.backgroundRole(), item._ok_color)
                delattr(item, '_ok_color')
                item.setAutoFillBackground(False)
                item.setPalette(pal)
                
