import holoviews as hv
from holoviews import opts
import bokeh.palettes
hv.extension('bokeh')
hv.opts.defaults(opts.NdOverlay(height=400,
                                width=600,
                                legend_position='right',
                                legend_offset=(10,0)))

def plot_growthcurves(data=None,
                      yaxis=None,
                      xaxis='Time [hr]',
                      colorby=None, # In progress
                      plotby=None, # Not coded yet
                      stride=1, # Not coded yet
                      show_whiskers=True, # Not coded yet
                      palette=None):
    
    # data.sort_values()
    
    # Set options
    # base_opts = dict(height=height, width=width, padding=0.1)
    data = data.sort_values(xaxis)
    
    # Simplest case, single curve:
    if ((colorby == None) & (plotby == None)):
        
        return hv.Curve(data,
                        kdims=[xaxis,colorby],
                        vdims=yaxis)
    
    # Multi-lines and multi-plots case:
    if ((colorby != None) & (plotby != None)):
        
        # Check to ensure the supplied column names exists
        if colorby not in data.columns:
            raise RunTimeError(f"Supplied colorby column name {colorby} does not exist. Spelling must match intended column name in dataframe.")
        
        if plotby not in data.columns:
            raise RunTimeError(f"Supplied plotby column name {plotby} does not exist. Spelling must match intended column name in dataframe.")
        
        # Check to ensure the palette can support n_colorby_cats
        n_colorby_cats = data[colorby].nunique()
        
        if palette is None:
        
            if n_colorby_cats > 10:
                raise RunTimeError(f"There are not enough colors in the palette to support the number of categories in {colorby}. Please specify a palette with at least {n_colorby_cats} colors.") 
            
            palette = bokeh.palettes.Category10[n_colorby_cats]
            
        elif n_colorby_cats > len(palette):
                raise RunTimeError(f"There are not enough colors in the palette to support the number of categories in {colorby}. Please specify a palette with at least {n_colorby_cats} colors.") 
        
        # Set the color map to the number of labels in that column
        cmap = hv.Cycle(palette)
        
        # Pull out available encodings (column names)
        encodings = [*list(data.columns)]
        
        chart = hv.Curve(
                    data,
                    [xaxis],
                    [yaxis, *encodings],
                ).groupby(
                    [colorby, plotby],
                ).opts(
                    color=cmap,
                ).overlay(
                    colorby
                ).layout(
                    plotby
                ).cols(2)
            
        return chart
                        
        
        
    #if ((colorby == None) & (plotby != None)):
        
        
    