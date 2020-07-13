import holoviews as hv
import numpy as np
from holoviews import opts
import bokeh.palettes
hv.extension('bokeh')
hv.opts.defaults(opts.NdOverlay(height=250,
                                width=400,
                                legend_position='right',
                                legend_offset=(10,0)))

def check_replicates(df, variable, value, grouping):
    """Checks for the presence of replicates in the values of a dataset,
    given some experimental conditions. Returns True if the standard
    deviation of the values of each group (if more than one exists) is
    greater than 0, indicating that replicates were performed under the
    given criteria. 
    
    Author: Patrick Almjhell, ArnoldLab@Caltech, 2019
    Adapted by: John Ciemniecki, NewmanLab@Caltech, 2020

    Parameters
    ----------
    df : Pandas DataFrame in tidy format
        The data set to be checked for replicates
    variable : immutable object
        Name of column of data frame for the independent variable,
        indicating a specific experimental condition.
    value : immutable object
        Name of column of data frame for the dependent variable,
        indicating an experimental observation.
    group : immutable object of list of immutable objects
        Column name or list of column names that indicates how the
        data set should be split.

    Returns
    -------
    replicates : boolean
        True if replicates are present.
    df_out : the DataFrame containing averaged 'variable' values, if
        replicates is True. Otherwise returns the original DataFrame.
    """

    # Unpack the experimental conditions into a single list of arguments
    if type(grouping) != list:
        grouping = [grouping]
        
    args = [elem for elem in [variable, *grouping] if elem != None]

    # Get stdev of argument groups
    grouped = df.groupby(args)[value]
    group_stdevs = grouped.std().reset_index()
    group_stdev = group_stdevs[value].mean()

    # Determine if there are replicates (mean of the stdevs > 0)
    replicates = bool(group_stdev > 0)

    # Average the values and return
    if replicates:
        df_describe = grouped.describe().reset_index()
        df_describe['std_err'] = df_describe['std'] / df_describe['count'].apply(np.sqrt)
        df_to_merge = df_describe[[variable, *grouping, 'mean', 'std', 'std_err']]
        df_to_merge = df_to_merge.rename(columns={'mean':'Mean of '+value,
                                                  'std':'Std of '+value,
                                                  'std_err':'Std Err of '+value})
#         df_mean = grouped.mean().reset_index()
#         df_std = grouped.std().reset_index()
#         df_mean.columns = list(df_mean.columns[:-1]) + ['Mean of ' + str(value)] 
#         df_std.columns = list(df_std.columns[:-1]) + ['Std of ' + str(value)]
#         df_
#         df_1 = df.merge(df_mean)
        df_return = df.merge(df_to_merge)
        
    else:
        df_return = df

    return replicates, df_return
    
    
def plot_growthcurves(data=None,
                      yaxis=None,
                      xaxis='Time [hr]',
                      colorby=None, # Not fully coded yet
                      plotby=None, # Not fully coded yet
                      palette=None,
                      yaxis_log=True,
                      height=250, # Not coded yet
                      width=400, # Not coded yet
                      cols=2,
                      show_all_data=True):
                      # publication_opts=True, # Not coded yet
                      # stride=1, # Not coded yet
    
     """Plots growth curves from a tidy dataframe.

    kwargs
    ----------
    data : (DataFrame) growth curve data in tidy format
    yaxis : (string) name of column in data to be plotted on y axis
    xaxis : (string) name of column in data to be plotted on x axis.
        Default assumes data was supplied from import_growthcurve function 
        in dknlab_tools and therefore has x axis name 'Time [hr]'.
    colorby : (string) name of column variable in data to color the 
        growth curves by
    plotby : (string) name of column variable in data to plot the 
        growth curves by
    palette : (list) color palette to use. If None is supplied, will use
        Category10 palette by default. (can find others in bokeh.palettes)
    yaxis_log : (boolean) to toggle display of log axes in y.
    height : (int) height of individual plots
    width : (int) width of individual plots
    cols : (int) number of columns to display the plots in
    show_all_data : (boolean) to toggle display of individual replicates.
        Not sure why you'd want to change this, but here it is.
    
    
    Returns
    -------
    chart : (NdOverlay) exploratory plot of growth curves
    """
    
    
    # Sort values for proper plotting of time series
    data = data.sort_values(xaxis)
    
    # Pull out available encodings (column names)
    encodings = [*list(data.columns)]
    
    ##############
    # Simplest case, single curve:
    ##############
    if ((colorby == None) & (plotby == None)):
        
        palette = bokeh.palettes.Category10[10]
        cmap = hv.Cycle(palette)
        
        curve= hv.Curve(
                    data,
                    kdims=[xaxis],
                    vdims=[yaxis,*encodings]
                ).groupby(
                    'well',
                ).opts(
                    color=cmap,
                    logy=True
                ).overlay(
                    'well')
        
        chart = curve
            
        return chart
        
    ##############
    # Multi-color case:
    ##############
    if ((colorby != None) & (plotby == None)):
        
        
    ##############
    # Multi-plot case:
    ##############
    if ((colorby == None) & (plotby != None)):
        
    
    ##############
    # Multi-color and multi-plot case:
    ##############
    if ((colorby != None) & (plotby != None)):
        
        # Check to ensure the supplied column names exists
        if colorby not in data.columns:
            raise RuntimeError(f"Supplied colorby column name {colorby} does not exist. Spelling must match intended column name in dataframe.")
        
        if plotby not in data.columns:
            raise RuntimeError(f"Supplied plotby column name {plotby} does not exist. Spelling must match intended column name in dataframe.")
            
        # Check to ensure the palette can support n_colorby_cats
        n_colorby_cats = data[colorby].nunique()
        
        if palette is None:
        
            if n_colorby_cats > 10:
                raise RuntimeError(f"There are not enough colors in the palette to support the number of categories in {colorby}. Please specify a palette with at least {n_colorby_cats} colors.") 
            elif n_colorby_cats < 3:
                palette = bokeh.palettes.Category10[3]
            else:
                palette = bokeh.palettes.Category10[n_colorby_cats]
            
        elif n_colorby_cats > len(palette):
                raise RuntimeError(f"There are not enough colors in the palette to support the number of categories in {colorby}. Please specify a palette with at least {n_colorby_cats} colors.") 
        
        
        replicates, data = check_replicates(data,
                                            'Time [hr]',
                                            yaxis,
                                            [colorby,plotby])
        
        if replicates:
            value = yaxis
            yaxis = 'Mean of '+yaxis
        
        # Set the color map to the number of labels in that column
        cmap = hv.Cycle(list(palette))
        
        curve = hv.Curve(
                    data,
                    [xaxis],
                    [yaxis, *encodings],
                ).groupby(
                    [colorby, plotby],
                ).opts(
                    color=cmap,
                    logy=yaxis_log,
                ).overlay(
                    colorby
                ).layout(
                    plotby
                ).cols(cols)
        
        if replicates & show_all_data:
            scatter = hv.Scatter(
                           data,
                           [xaxis],
                           [value, *encodings],
                       ).groupby(
                           [colorby, plotby],
                       ).opts(
                           color=cmap,
                           logy=yaxis_log,
                           alpha=0.25,
                       ).overlay(
                           colorby
                       ).layout(
                           plotby
                       ).cols(cols)
            
            chart = scatter * curve
        else:
            chart = curve
            
        return chart