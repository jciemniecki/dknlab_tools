import pandas as pd
import datetime
import numpy as np


def plate_condmap(filename, 
                  verbose=False,
                  delimiter=';'):
    """Imports a specific 96-well label legend in excel
    (found in dknlab_tools > templates) and outputs a tidy 
    dataframe of the well labels.
    
    Parameters
    ----------
    filename : (string) filepath to the filled-out 
        excel template
    verbose : (boolean) whether or not the supplied condition
        map is in a verbose format; that is, with every condition
        specified even when the concentration of an addition is 0.
        Example: "PI, PYO, PCA; 5, 0, 0". This is opposed to the 
        non-verbose formatting, where the same condition would be
        specified as "PI; 5".
    delimiter : (string) delimiter for parsing concentrations 
        from descriptors

    Returns
    -------
    df : (DataFrame) tidy, with index of well names (e.g., 'A4')
        and all the labels filled into the excel template
    """
    
    # Read in excel condition map
    df = pd.read_excel(filename, dtype=str)
    
    
    # Melt column names (1, 2, etc) into their own df column
    df = df.melt(id_vars=['variable','row'], 
                 value_vars=[1,2,3,4,5,6,7,8,9,10,11,12],
                 var_name='column')
    
    # Reformat into well identifier (A1, A2, etc)
    df['Well'] = df['row'].apply(str) + df['column'].apply(str)
    df.drop(columns = ["row", "column"], inplace=True)
    df = df.dropna(axis=0)
    
    # Pivot to be tidy, then eliminate extra index names
    df = df.pivot(index='Well', columns='variable')
    df.columns = df.columns.droplevel(0)
    df = df.rename_axis(columns=None)
    
    # Split medium column
    media = df['Medium; Concentration (mM)'].str.split(delimiter, 
                                                      n=1, 
                                                      expand=True)  
    # Add Medium column to df
    df['Medium'] = media[0]
    
    # If user supplied a medium concentration, add to df
    if len(media.columns) > 1:
        
        df['Medium Conc. (mM)'] = media[1].astype(float)
    
    # Drop original, unsplit media column
    df.drop(columns =['Medium; Concentration (mM)'], inplace=True)
    
    # Split condition column off
    conditions = df['Condition; Concentration (µM)'].str.split(delimiter, 
                                                                n=1, 
                                                                expand=True) 
    # Add Condition column to df
    df['Condition'] = conditions[0]
    
    # If user supplied condition concentration, add to df
    if len(conditions.columns) > 1:
        
        df['Condition Conc. (µM)'] = conditions[1]
        
        # If the user has input conditions in a verbose manner, 
        # add separate concentration columns to df for each
        if verbose == True:
            
            names_array = conditions[0].unique()
            names_array = names_array[~pd.isnull(names_array)]
            
            if len(names_array)>1:
                raise RuntimeError(f"""Legend is not verbose; ensure all condition descriptors left of semicolor are typed exactly the same in every well. Found the following different names: {names_array}""")
            names = names_array[0].split(',')
            
            concs = conditions[1].str.split(',', expand=True)
            
            if len(names) != len(concs.columns):
                raise RuntimeError(f"""Legend is not verbose; ensure the same number of condition concentrations are to the right of semicolor in every well. Supplied {len(names)} condition names but {len(concs.columns)} condition concentrations.""")
            
            for i in range(len(names)):
                name = names[i].rstrip().lstrip()
                concs = concs.rename(columns = {i:name+' Conc. (µM)'})
            
            concs = concs.astype('float')
            df = pd.concat([df, concs], axis = 1)

            # Remove superfluous condition and multi-concentration columns
            df.drop(columns =['Condition'], inplace=True)
            df.drop(columns =['Condition Conc. (µM)'], inplace=True)
        
    # Drop original, unsplit condition column
    df.drop(columns =['Condition; Concentration (µM)'], inplace=True)
    
    return df


def _str2hours(datetime_string):
    """Converts excel datetime format to decimal hours.
    
    Parameters
    ----------
    datetime_string : (string)
    
    Returns
    -------
    time_in_hours : (float)
    """
    
    # If over 24 hours, will convert 'date HH:MM:SS' to 'HH:MM:SS' 
    # and store number of hours to account for
    if ' ' in datetime_string:
        days, time_string = datetime_string.split()
        accounted_hours = int(days[-2:]) * 24
    else:
        time_string = datetime_string
        accounted_hours = 0
    
    # Grab the numbers
    hours, minutes, seconds = time_string.split(':', 2)
    
    # Check that all values are numbers
    if not ((hours.isdigit()) & (minutes.isdigit()) & (seconds.isdigit())): 
        raise RuntimeError("""Time format within the data is improper. Verify that all time points are in the format hours:minutes:seconds.""")
                                  
    # Convert to floats for math
    hours = float(hours) + accounted_hours
    minutes = float(minutes)
    seconds = float(seconds)
    
    # Check that input was in proper format 
    if not ((minutes < 60) & (seconds < 60)):
        raise RuntimeError("""Time format within the data is improper. Verify that minutes and seconds values are less than 60.""")
    
    # Convert
    min_as_hours = minutes / 60
    sec_as_hours = seconds / 3600
    time_in_hours = hours + min_as_hours + sec_as_hours
    
    # Round to decimal place that preserves 1 second differences fully
    return round(time_in_hours, 3)


def wrangle_growthcurves(filename, new_bioteks=True):
    """Imports Biotek's default excel output for time-course data,
    parses out separate measurement types (if there are multiple).
    
    Parameters
    ----------
    filename : (string) filepath to the Tecan excel output
    
    new_bioteks : (boolean) if using default output of new or old biotek plate readers
    
    Returns
    -------
    df_list : (tuple of DataFrames) each tidied, one per
        measurement
    """
    
    # Import data, immediately drop any rows that have all NaN values.
    df = pd.read_excel(filename, sheet_name=0, header=None)
    
    # New bioteks output data with a spacer column and with time instead of kinetic read as time label
    # The rows variable indicates start/end of a measurement type
    if new_bioteks==True:
        data_col=1
        label_spacer=2
        rows = ['Time']
    else:
        data_col=0
        label_spacer=1
        rows = ['Kinetic read']
        
    # Make an iterable of those row numbers plus the end of the dataframe
    m_inds = df[df[df.columns[data_col]].isin(rows)].index
    n_measurements = len(m_inds)
    m_inds = m_inds.union([len(df)+3])

    # Instantiate list of size n per measurement type
    df_list = [0] * n_measurements
    
    # Instantiate empty list to hold names of measurements
    measurement_list = []

    # Put dataframes into df_list
    # (one per measurement) and tidy them
    for i in range(n_measurements):
        
        # If there is a row above 'Kinetic read'/'Time' store it 
        # as the name of the measurement type
        if (m_inds[i]-1) >= 0:
            m = str(df.iloc[m_inds[i]-label_spacer,0])
            measurement_list.append(m)
        else:
            measurement_list.append('value'+str(i))
        
        # Grab the relevant excel inds
        start_ind = m_inds[i]
        size = m_inds[i+1]-m_inds[i]-3
        
        # Load in sub-df from excel file
        df_list[i] = pd.read_excel(filename, 
                                   skiprows=start_ind, 
                                   nrows=size)
        
        # Pull out the timepoints, in decimal hours,
        # from the STUPID excel datetime format
        # using custom _str2hours function
        hours = df_list[i][rows[0]].astype('str').apply(_str2hours)

        # Add a time column in units of hours
        df_list[i]['Time [hr]'] = hours
        
        # Melt all the well identifier columns (e.g. A1, A2, etc.)
        df_list[i] = pd.melt(df_list[i],
                             id_vars=['Time [hr]',rows[0]])
        
        # Rename the new, ambiguously named columns
        df_list[i] = df_list[i].rename(
                                    columns={'variable':'Well','value':m})
        
        # Delete Kinetic read column
        df_list[i] = df_list[i].drop(rows[0], axis=1)
        
        # Delete any rows that remain with 'OVRFLW', NaN, or T˚ values
        df_list[i][m] = pd.to_numeric(df_list[i][m], errors='coerce')
        df_list[i] = df_list[i].dropna(how='any')
        df_list[i] = df_list[i][df_list[i]["Well"].str.contains("T")==False]
    
#     if merged == True:
        
#         # loop over number of measurments to merge
#         for i, m in enumerate(measurement_list):
            
#             # instantiate new df on first loop
#             if i == 0:
#                 df_out = df_list[i]
                
#             # merge measurment m to the output dataframe
#             if i > 0:
#                 mini_df = df_list[i][['Well', 'Time [hr]', m]]
#                 df_out = pd.concat([df_out, mini_df], axis=0)
    
#         return df_out
    
#     else:
    return tuple(df_list)
    
    
def import_growthcurves(data_file_path, 
                        condition_map_file_path,
                        new_bioteks=True,
                        verbose=False):
    """Imports Biotek data with a condition map and outputs a collection
    of tidy dataframes ready for EDA with the viz module.
    
    Parameters
    ----------
    data_file_path : (string) filepath to the Biotek excel output
    condition_map_file_path : (string) filepath to the specific, filled-out 
        excel template
    new_bioteks : (boolean) if using default output of new or old biotek plate readers
    verbose : (boolean) whether or not the supplied condition
        map is in a verbose format; that is, with every condition
        specified even when the concentration of an addition is 0.
        Example: "PI, PYO, PCA; 5, 0, 0". This is opposed to the 
        non-verbose formatting, where the same condition would be
        specified as "PI; 5".

    Returns
    -------
    df_list : (tuple of DataFrame) each tidy, each annotated
    """
    
    df_data = wrangle_growthcurves(data_file_path, new_bioteks=True)
    
    condition_df = plate_condmap(condition_map_file_path, verbose=verbose)
    
    df_list = [df.merge(condition_df, on='Well') for df in df_data]
    
    return tuple(df_list)