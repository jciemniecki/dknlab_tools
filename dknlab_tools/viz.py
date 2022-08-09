import holoviews as hv
import numpy as np
from holoviews import opts
import pandas as pd
import bokeh.palettes
import scipy.interpolate
hv.extension('bokeh')
hv.opts.defaults(opts.NdOverlay(legend_position='right',
                                legend_offset=(10,0)))

def _check_replicates(df, variable, value, grouping):
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

def _check_columns(check, df):
    
    if isinstance(check, list):
        for name in check:
            if name not in df.columns:
                raise RuntimeError(f"Supplied column name {name} does not exist. Spelling must match intended column name in dataframe.")
    else:
            if check not in df.columns:
                raise RuntimeError(f"Supplied column name {check} does not exist. Spelling must match intended column name in dataframe.")
    
def _check_palette(palette, colorby, data, plotby=None):
    
    # If only colorby is passed, number of colors is equal to size of colorby
    # If there is both a plotby and colorby, first the data are grouped by
    # plotby, then each plot dataset is grouped by colorby to determine the
    # max number of colors needed.
    if plotby==None:
        n_colorby_cats = data.groupby(colorby).ngroups
    else:
        plot_groups = data.groupby(plotby)
        plot_groups_colorby_cats = []
        for _, group in plot_groups:
            plot_groups_colorby_cats.append(group.groupby(colorby).ngroups)
        n_colorby_cats = max(plot_groups_colorby_cats)
        
    if palette is None:
    
        if n_colorby_cats > 10:
            raise RuntimeError(f"There are not enough colors in the palette to support the number of categories in {colorby}. Please specify a palette with at least {n_colorby_cats} colors.") 
            
        elif n_colorby_cats < 3:
            return bokeh.palettes.Category10[3]
        
        else:
            return bokeh.palettes.Category10[n_colorby_cats]
        
    elif n_colorby_cats > len(palette):
        raise RuntimeError(f"There are not enough colors in the palette to support the number of categories in {colorby}. Please specify a palette with at least {n_colorby_cats} colors.")
    else:
        return palette
    
def plot_growthcurves(data=None,
                      yaxis=None,
                      xaxis='Time [hr]',
                      colorby=None, 
                      plotby=None, 
                      palette=None,
                      yaxis_log=True,
                      height=350,
                      width=500,
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
    ylim : (tuple) to set the y axis range.
    height : (int) height of individual plots
    width : (int) width of individual plots
    cols : (int) number of columns to display the plots in
    show_all_data : (boolean) to toggle display of individual replicates.
        Not sure why you'd want to change this, but here it is.
    
    
    Returns
    -------
    chart : (NdOverlay) exploratory plot of growth curves
    """
    
    # Ensure supplied x and y axis exist within dataframe
    _check_columns(xaxis, data)
    _check_columns(yaxis, data)
    
    # Sort values for proper plotting of time series
    data = data.sort_values(xaxis)
    
    # Pull out available encodings (column names)
    encodings = [*list(data.columns)]
    
    ##############
    # Simplest case, single curve:
    ##############
    if ((colorby == None) & (plotby == None)):
        
        palette = _check_palette(palette, 'Well', data)
        cmap = hv.Cycle(palette)
        
        curve= hv.Curve(
                    data,
                    kdims=[xaxis],
                    vdims=[yaxis,*encodings]
                ).groupby(
                    'Well',
                ).opts(
                    color=cmap,
                    logy=yaxis_log,
                    muted_line_alpha=0.0,
                    height=height,
                    width=width,
                ).overlay(
                    'Well')
            
        return curve
        
    ##############
    # Multi-color case:
    ##############
    if ((colorby != None) & (plotby == None)):
        
        if not isinstance(colorby, list):
            colorby = [colorby]
        
        # Check supplied column names are in dataframe
        _check_columns(colorby, data)
            
        # Check to ensure the palette is large enough to support the data
        # If no palette was supplied, set to default Category10
        palette = _check_palette(palette, colorby, data)
        
        # Check for replicates
        replicates, data = _check_replicates(data,
                                             xaxis,
                                             yaxis,
                                             colorby)
        
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
                    [*colorby],
                ).opts(
                    color=cmap,
                    logy=yaxis_log,
                    muted_line_alpha=0.0,
                ).overlay(
                    [*colorby]
                )
        
        if replicates & show_all_data:
            scatter = hv.Scatter(
                           data,
                           [xaxis],
                           [value, *encodings],
                       ).groupby(
                           [*colorby],
                       ).opts(
                           color=cmap,
                           logy=yaxis_log,
                           alpha=0.25,
                           muted_fill_alpha=0.0,
                           muted_line_alpha=0.0,
                       ).overlay(
                           [*colorby]
                       )
            
            chart = scatter * curve
        else:
            chart = curve
        
        chart.opts(height=height, width=width)
        
        return chart
        
    ##############
    # Multi-plot case:
    ##############
    if ((colorby == None) & (plotby != None)):
        
        if not isinstance(plotby, list):
            plotby = [plotby]
        
        # Check supplied column names are in dataframe
        _check_columns(plotby, data)
        
        # Check for replicates
        replicates, data = _check_replicates(data,
                                             xaxis,
                                             yaxis,
                                             plotby)
        
        if replicates:
            value = yaxis
            yaxis = 'Mean of '+yaxis
            
        curve = hv.Curve(
                    data,
                    [xaxis],
                    [yaxis, *encodings],
                ).groupby(
                    [*plotby],
                ).opts(
                    logy=yaxis_log,
                    height=height,
                    width=width,
                ).layout(
                    [*plotby]
                ).cols(
                    cols)
        
        if replicates & show_all_data:
            scatter = hv.Scatter(
                           data,
                           [xaxis],
                           [value, *encodings],
                       ).groupby(
                           [*plotby],
                       ).opts(
                           logy=yaxis_log,
                           alpha=0.25,
                           muted_fill_alpha=0.0,
                           muted_line_alpha=0.0,
                           height=height,
                           width=width,
                       ).layout(
                           [*plotby]
                       ).cols(cols)
            
            chart = scatter * curve
        else:
            chart = curve

        return chart
    
    ##############
    # Multi-color and multi-plot case:
    ##############
    if ((colorby != None) & (plotby != None)):
        
        if not isinstance(colorby, list):
            colorby = [colorby]
        if not isinstance(plotby, list):
            plotby = [plotby]
        
        # Check to ensure the supplied column names exists
        _check_columns(colorby, data)
        _check_columns(plotby, data)
            
        # Check to ensure the palette is large enough to support the data
        # If no palette was supplied, set to default Category10
        palette = _check_palette(palette, colorby, data, plotby=plotby)
        
        # Check for replicates
        replicates, data = _check_replicates(data,
                                             xaxis,
                                             yaxis,
                                             [*colorby,*plotby])
        
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
                    [*colorby, *plotby],
                ).opts(
                    color=cmap,
                    logy=yaxis_log,
                    muted_alpha=0.0,
                    height=height,
                    width=width,
                ).overlay(
                    [*colorby]
                ).layout(
                    [*plotby]
                ).cols(cols)
        
        if replicates & show_all_data:
            scatter = hv.Scatter(
                           data,
                           [xaxis],
                           [value, *encodings],
                       ).groupby(
                           [*colorby, *plotby],
                       ).opts(
                           color=cmap,
                           logy=yaxis_log,
                           alpha=0.25,
                           muted_fill_alpha=0.0,
                           muted_line_alpha=0.0,
                           height=height,
                           width=width,
                       ).overlay(
                           [*colorby]
                       ).layout(
                           [*plotby]
                       ).cols(cols)
            
            chart = scatter * curve
        else:
            chart = curve
            
        return chart
    
def plot_SYTO9_PI(data=None,
                  groups_to_plot=None,
                  xaxis='Position Z (µm)',
                  palette=None,
                  volume_yaxis_log=True,
                  height=400,
                  width=700,
                  show_all_data=True,
                  save_smoothed=False):
    
    data = data[data['File'].isin(groups_to_plot)].sort_values(by=xaxis)
    smoothed_df = pd.DataFrame()#columns=['Position Z','Smoothed Volume','Smoothed PI Intensity','Smoothed SYTO9 Intensity','ID','File'])
    
    # Code below from BeBi103a lesson "Time Series Data", written by Justin Bois 2019
    # Adapted by John Ciemniecki 2021
    #------------
    for group in groups_to_plot:
        
        results_df=pd.DataFrame()
        
        temp = data[data['File']==group]
        
        # Determine smoothing factor from rule of thumb (use f = 0.05)
        #smooth_factor_volume = 0.05 * (temp['Volume']**2).sum()
        smooth_factor_SYTO9 = 0.05 * (temp['SYTO-9 Intensity (AU)']**2).sum()
        smooth_factor_PI = 0.05 * (temp['PI Intensity (AU)']**2).sum()
        
        # Set up a scipy.interpolate.UnivariateSpline instance
        Zs = temp[xaxis].values
        #Vs = temp['Volume'].values
        Ss = temp['SYTO-9 Intensity (AU)'].values
        Ps = temp['PI Intensity (AU)'].values
        
        #Vspl = scipy.interpolate.UnivariateSpline(Zs, Vs, s=smooth_factor_volume)
        Sspl = scipy.interpolate.UnivariateSpline(Zs, Ss, s=smooth_factor_SYTO9)
        Pspl = scipy.interpolate.UnivariateSpline(Zs, Ps, s=smooth_factor_PI)
        
        # spl is now a callable function
        Zs_spline = np.linspace(Zs[0], Zs[-1], 500)
        #Vs_spline = Vspl(Zs_spline)
        Ss_spline = Sspl(Zs_spline)
        Ps_spline = Pspl(Zs_spline)
        
        results_df[xaxis] = Zs_spline
        #results_df['Smoothed Volume'] = Vs_spline
        results_df['Smoothed PI Intensity'] = Ps_spline
        results_df['Smoothed SYTO-9 Intensity'] = Ss_spline
        results_df['File'] = group
        
        # Will include, not sure if I can trust the order has been maintained
        results_df['ID'] = temp['ID']
        
        smoothed_df = smoothed_df.append(results_df)
                                        
    #-----------
    
    # Plot results
    v_plot = hv.Scatter(data=data,
                        kdims=xaxis,
                        vdims=['Volume (µm^3)', 'File']
                    ).groupby(
                        'File'
                    ).opts(
                        height=height,
                        width=width,
                        logy=volume_yaxis_log,
                        alpha=0.25,
                        muted_fill_alpha=0.0,
                        muted_line_alpha=0.0,
                        padding=0.1,
                    ).overlay()
    
    s_plot = hv.Scatter(data=data,
                        kdims=xaxis,
                        vdims=['SYTO-9 Intensity (AU)', 'File']
                    ).groupby(
                        'File'
                    ).opts(
                        height=height,
                        width=width,
                        alpha=0.25,
                        muted_fill_alpha=0.0,
                        muted_line_alpha=0.0,
                    ).overlay()
    
    p_plot = hv.Scatter(data=data,
                        kdims=xaxis,
                        vdims=['PI Intensity (AU)', 'File']
                    ).groupby(
                        'File'
                    ).opts(
                        height=height,
                        width=width,
                        alpha=0.25,
                        muted_fill_alpha=0.0,
                        muted_line_alpha=0.0,
                    ).overlay()
    
#     vs_plot = hv.Curve(data=smoothed_df,
#                        kdims=xaxis,
#                        vdims=['Smoothed Volume', 'File']
#                     ).groupby(
#                        'File'
#                     ).opts(
#                        height=height,
#                        width=width,
#                        logy=volume_yaxis_log,
#                        muted_alpha=0,
#                        padding=0.1,
#                     ).overlay()
    
    ss_plot = hv.Curve(data=smoothed_df,
                       kdims=xaxis,
                       vdims=['Smoothed SYTO-9 Intensity', 'File']
                    ).groupby(
                       'File'
                    ).opts(
                       height=height,
                       width=width,
                       muted_alpha=0,
                    ).overlay()
    
    ps_plot = hv.Curve(data=smoothed_df,
                       kdims=xaxis,
                       vdims=['Smoothed PI Intensity', 'File']
                    ).groupby(
                       'File'
                    ).opts(
                       height=height,
                       width=width,
                       muted_alpha=0,
                    ).overlay()
    
    
    return (v_plot) + (s_plot * ss_plot) + (p_plot * ps_plot)

    
    
def save(plot, filename, filetype='html'):
    """
    Saves supplied plot with the supplied filename. Default
    format is html. Can also save as png.
    """
    if filetype=='svg':
        raise RuntimeError("svg format not supported with Bokeh backend in Holoviews.")
                           
    hv.save(plot, filename, fmt=filetype)
    
    
    
def _lin_regression_timeseries(data, xaxis, yaxis, time_range):
    # y = mx+b --> y = Ap where A = [x,1] and p = [m,b]
    df = data[(data[xaxis]>=time_range[0]) & (data[xaxis]<=time_range[1])]
    t = df[xaxis].to_numpy()
    A = np.c_[t, np.ones(len(t))]
    y = df[yaxis].to_numpy()
    m, b = np.linalg.lstsq(A,y,rcond=None)[0]
    return m



def plot_slopes(data=None,
                xaxis='Time [hr]',
                yaxis=None,
                time_range=None,
                invert_slope=False,
                plotby=None,
                groupby=None,
                replicates_over='Well',
                yaxis_label='Rate of change',
                yaxis_log=False,
                multiply_by=None,
                height=400,
                width=500,
                return_slopes=False):
    
    """Plots slopes of time series data from dknlab_tools.import_growthcurves().

    kwargs
    ----------
    data : (DataFrame) assumes a tidy dataframe specifically from dknlab_tools.import_growthcurves(), but any tidy dataframe should also work,
    xaxis : (String) column of dataframe to use as the x axis during the linear fit,
    yaxis : (String) column of dataframe to use as the y axis during the linear fit,
    time_range : (List of 2 ints or floats) range of supplied xaxis to perform a linear fit over,
    invert_slope : (Boolean) if True, inverts the sign of slope values,
    plotby : (String or List) column(s) of dataframe to groupby into separate output plots of the data,
    groupby : (String or List) column(s) of dataframe to group data by; resulting groups will be the categories on the x axis of the output plot,
    replicates_over : (String) column of dataframe that separates the replicates. For example, replicates are over different wells in a 96-well plate format. Pass None if dataset does not contain replicates.
    yaxis_label : (String) label on yaxis of output plot,
    yaxis_log : (Boolean) if True, plots slopes on a log axis,
    multiply_by : (Float) value to multiply all slopes by, generally for transforming units of slope values,
    height : (Int) height of plot(s),
    width : (Int) width of plot(s)m
    return_slopes : (Boolean) if True, function additionally returns a DataFrame of the slope values organized in a tidy dataframe
    
    Returns
    -------
    chart : (NdOverlay) exploratory plot of slopes
    slopes : (DataFrame) tidy dataframe of slope values
    """

    df = pd.DataFrame(data)
    
    if multiply_by!=None and not isinstance(multiply_by,float):
        raise RuntimeError('multiply_by must be a float.')
    
    if (plotby!=None) and (type(plotby) is not list):
        plotby = [plotby]
    if groupby==None:
        raise RuntimeError('Must specify at least one column to group by for plotting.')
    elif type(groupby) is not list:
        groupby = [groupby]
    
    # create new cols that are concatenations of cols specified by kwargs
    if plotby==None:
        df['plotby'] = ''
    elif len(plotby)==1:
        df['plotby'] = df[plotby]
    else:
        df['plotby'] = df[plotby].apply(lambda row: ', '.join(row.values.astype(str)), axis=1)
    
    if len(groupby)==1:
        df['groupby'] =df[groupby]
    else:
        df['groupby'] = df[groupby].apply(lambda row: ', '.join(row.values.astype(str)), axis=1)
    
    # calculate slopes within specified time_range of each well while retaining relevant labels
    # if invert_slopes is True, take inverse
    # if user has specified a value for multiply_by, multiply slopes by that value
    if replicates_over==None:
        gg = ['plotby','groupby']
    else:
        gg = ['plotby','groupby',replicates_over]
    
    slopes = df.groupby(gg).apply(_lin_regression_timeseries, (xaxis), (yaxis), (time_range))
    slopes = pd.DataFrame(slopes).reset_index()
    slopes = slopes.rename(columns={0:yaxis_label})
    if invert_slope==True:
        slopes[yaxis_label] = -slopes[yaxis_label]
    if multiply_by!=None:
        slopes[yaxis_label] = slopes[yaxis_label] * multiply_by
    
    # if there is only one plot to make:
    if plotby==None:
        
        plot = hv.BoxWhisker(slopes,
                          kdims='groupby',
                          vdims=yaxis_label
                        ).opts(
                          height=height,
                          width=width,
                          box_color='groupby',
                          cmap='Category20',
                          #size=10,
                          logy=yaxis_log,
                          #fill_alpha=0.1,
                          xlabel=', '.join(groupby),
                          show_grid=True,
                          show_legend=False,
                          padding=0.1,
                          #jitter=0.2,
                          xrotation=45
                        )
    
    # if the user has specified multiple plots to be made:
    else:
            
        plot = hv.BoxWhisker(slopes,
                          kdims=['groupby','plotby'],
                          vdims=yaxis_label
                        ).groupby(
                          ['plotby']
                        ).opts(
                          height=height,
                          width=width,
                          box_color='groupby',
                          cmap='Category20',
                          #size=10,
                          show_legend=False,
                          logy=yaxis_log,
                          #fill_alpha=0.1,
                          xlabel=', '.join(groupby),
                          show_grid=True,
                          padding=0.1,
                          #jitter=0.2,
                          xrotation=45
                        ).layout(
                          ['plotby']
                        )
    
    if return_slopes==True:
        return plot, slopes
    else:
        return plot
    

    
def _growthrate_timeseries(data, xaxis, yaxis, n_timepoints):
    
    dt = n_timepoints - 1
    t = data[xaxis].to_numpy()
    y = np.log(data[yaxis].to_numpy()) # this is natural log, NOT log base 10
    mu_inst = [(y[i]-y[i-dt])/(t[i]-t[i-dt]) for i in range(dt, len(min([t,y], key=len)))]
    mu_max = max(mu_inst)
    
    # mu_max has an index that is shifted by dt relative to the corresponding time array
    mu_max_ind = mu_inst.index(mu_max) + dt 
    time_range = (t[mu_max_ind-dt], t[mu_max_ind])
    
    # mu_max is in hr^-1, doubling time is in hours, multiply by 60 for minutes
    t_doubling = np.log(2) / mu_max * 60
    
    return pd.Series({0: mu_max, 'T_d (min)':t_doubling, 'Time Range': time_range})



def plot_growthrates(data=None,
                     xaxis='Time [hr]',
                     yaxis=None,
                     n_timepoints=6,
                     plotby=None,
                     groupby=None,
                     replicates_over='Well',
                     yaxis_label='µ (hr^-1)',
                     multiply_by=None,
                     height=400,
                     width=300,
                     return_growthrates=False):
    """
    Plots specific growth rate µ in units of hr^-1 of data from dknlab_tools.import_growthcurves().\n
    Note that for proper fit data should be collected in such a way so that there are at least six measurements\n
    during the exponential growth of the curve. This can be achieved by increasing the frequency of measurement\n
    (every 15 min is usually sufficient) and/or decreasing the initial innoculum size.\n
    \n
    Algorithm used is a sliding window slope calculation of semilog data. Maximum slope along the curve is returned.
    
    kwargs
    ----------
    data : (DataFrame) assumes a tidy dataframe specifically from dknlab_tools.import_growthcurves(), but any tidy dataframe should also work,
    xaxis : (String) column of dataframe to use as the x axis during the linear fit,
    yaxis : (String) column of dataframe to use as the y axis during the linear fit,
    time_range : (List of 2 ints or floats) range of supplied xaxis to perform a linear fit over,
    invert_slope : (Boolean) if True, inverts the sign of slope values,
    plotby : (String or List) column(s) of dataframe to groupby into separate output plots of the data,
    groupby : (String or List) column(s) of dataframe to group data by; resulting groups will be the categories on the x axis of the output plot,
    replicates_over : (String) column of dataframe that separates the replicates. For example, replicates are over different wells in a 96-well plate format. Pass None if dataset does not contain replicates.
    yaxis_label : (String) label on yaxis of output plot,
    yaxis_log : (Boolean) if True, plots slopes on a log axis,
    multiply_by : (Float) value to multiply all slopes by, generally for transforming units of slope values,
    height : (Int) height of plot(s),
    width : (Int) width of plot(s)m
    return_slopes : (Boolean) if True, function additionally returns a DataFrame of the slope values organized in a tidy dataframe
    
    Returns
    -------
    chart : (NdOverlay) exploratory plot of growth rates
    slopes : (DataFrame) tidy dataframe of growth rates and time range of max growth
    """

    df = pd.DataFrame(data)
    
    if multiply_by!=None and not isinstance(multiply_by,float):
        raise RuntimeError('multiply_by must be a float.')
    
    if (plotby!=None) and (type(plotby) is not list):
        plotby = [plotby]
    if groupby==None:
        raise RuntimeError('Must specify at least one column to group by for plotting.')
    elif type(groupby) is not list:
        groupby = [groupby]
    
    # create new cols that are concatenations of cols specified by kwargs
    if plotby==None:
        df['plotby'] = ''
    elif len(plotby)==1:
        df['plotby'] = df[plotby]
    else:
        df['plotby'] = df[plotby].apply(lambda row: ', '.join(row.values.astype(str)), axis=1)
    
    if len(groupby)==1:
        df['groupby'] =df[groupby]
    else:
        df['groupby'] = df[groupby].apply(lambda row: ', '.join(row.values.astype(str)), axis=1)
    
    # find growth rate within sliding specified n_timepoints of each well while retaining relevant labels
    # if user has specified a value for multiply_by, multiply slopes by that value
    if replicates_over==None:
        gg = ['plotby','groupby']
    else:
        gg = ['plotby','groupby',replicates_over]
    
    rates = df.groupby(gg).apply(_growthrate_timeseries, (xaxis), (yaxis), (n_timepoints))
    rates = pd.DataFrame(rates).reset_index()
    rates = rates.rename(columns={0:yaxis_label})
    
    if multiply_by!=None:
        rates[yaxis_label] = rates[yaxis_label] * multiply_by
    
    # if there is only one plot to make:
    if plotby==None:
        
        plot = hv.BoxWhisker(rates,
                          kdims='groupby',
                          vdims=yaxis_label
                        ).opts(
                          height=height,
                          width=width,
                          box_color='groupby',
                          cmap='Category20',
                          #size=10,
                          #logy=yaxis_log,
                          #fill_alpha=0.1,
                          xlabel=', '.join(groupby),
                          show_grid=True,
                          show_legend=False,
                          padding=0.1,
                          #jitter=0.2,
                          xrotation=45
                        )
    
    # if the user has specified multiple plots to be made:
    else:
            
        plot = hv.BoxWhisker(rates,
                          kdims=['groupby','plotby'],
                          vdims=yaxis_label
                        ).groupby(
                          ['plotby']
                        ).opts(
                          height=height,
                          width=width,
                          box_color='groupby',
                          cmap='Category20',
                          #size=10,
                          show_legend=False,
                          #logy=yaxis_log,
                          #fill_alpha=0.1,
                          xlabel=', '.join(groupby),
                          show_grid=True,
                          padding=0.1,
                          #jitter=0.2,
                          xrotation=45
                        ).layout(
                          ['plotby']
                        )
    
    if return_growthrates==True:
        return plot, rates
    else:
        return plot