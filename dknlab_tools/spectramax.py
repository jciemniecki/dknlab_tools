import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import bokeh.io
import bokeh.plotting
from bokeh.models import Title

# Enable viewing Bokeh plots in the notebook
bokeh.io.output_notebook()

def MM(sub_conc, Vmax_asymp, Km):
    return Vmax_asymp * sub_conc / (Km + sub_conc)

def MM_kinetics(filename, ex_coeff, substrate_name, slope_column, protein_concentration, protein_name, storeplot = False):
    """Use to calculate Michaelis-Menten best fit curves
       Data will be plotted as Vmax (µM /s) vs substrate concentration (µM),
       for filename(string): input filename i.e. '~/Desktop/filename.csv',
       for ex_coeff(float or int): input extinction coefficient of substrate in M-1 cm-1,
       for substrate_name(string): input name of substrate, must match the name of your column in csv file,
       for slope_column(string): input column title for slope measurements,
       for protein concentration(float or int): input protein concentration in µM,
       for protein name(string): input name of your protein.
       """
    
    # Import file to pandas
    df = pd.read_csv(filename)
    
    # Useful factors
    permin_to_persec_factor = 1/60
    M_to_uM_factor = 1000 * 1000

    # Compute sp. activity
    df['Vmax_(uM_s-1)'] = df[slope_column] * M_to_uM_factor * permin_to_persec_factor / ex_coeff
    
    # Fit data to MM curve
    popt, pcov = curve_fit(MM, df[substrate_name], df['Vmax_(uM_s-1)'])
    pstdev = np.sqrt(np.diag(pcov))
    
    #calculate MM values
    Vmax_asymp = popt[0]
    Km = popt[1]
    kcat = Vmax_asymp / protein_concentration
    cat_eff = kcat / Km * M_to_uM_factor
    
    #Design labels for decimal rounding or sci notation 
    my_labels = f"""Km = {Km:.2f} µM, kcat = {kcat:.2e} s-1, catalytic efficiency = {cat_eff:.2e} s-1 M-1"""
    
    #Plot data
    p = bokeh.plotting.figure(
        frame_width=500,
        frame_height=350,
        x_axis_label='PYO concentration (µM)',
        y_axis_label='Vmax (µM / s)',
     )

    p.add_layout(Title(text= my_labels, text_font_style="normal", align = 'center'), 'above')
    p.add_layout(Title(text= protein_name, text_font_size="16pt", align = 'center'), 'above')

    p.circle(x= df[substrate_name],
             y = df['Vmax_(uM_s-1)'],
             line_color = 'black',
             line_width = 1,
             fill_color = 'pink',
             size = 7
            )
    
    p.line(x=df[substrate_name],
           y=MM(df[substrate_name], popt[0], popt[1]),
           color = 'black',
           line_width = 1.5
          )
    
    if storeplot == True:
        return p 
    else: 
        bokeh.io.show(p)