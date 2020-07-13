import pandas as pd
import datetime


def plate_condmap(filename, delimiter=';'):
    """Imports a specific 96-well label legend in excel
    (found in dknlab_tools > templates) and outputs a tidy 
    dataframe of the well labels.
    
    Parameters
    ----------
    filename : (string) filepath to the filled-out 
        excel template
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
    df['well'] = df['row'].apply(str) + df['column'].apply(str)
    df.drop(columns = ["row", "column"], inplace=True)
    
    # Pivot to be tidy, then eliminate extra index names
    df = df.pivot(index='well', columns='variable')
    df.columns = df.columns.droplevel(0)
    df = df.rename_axis(columns=None)
    
    # Split medium and condition columns
    media = df['Medium; Concentration (mM)'].str.split(delimiter, 
                                                      n=1, 
                                                      expand=True)  
    df['medium'] = media[0]
    if len(media.columns) > 1:
        df['[medium] (mM)'] = media[1]
    df.drop(columns =['Medium; Concentration (mM)'], inplace=True)
    
    conditions = df['Condition; Concentration (µM)'].str.split(delimiter, 
                                                                n=1, 
                                                                expand=True) 
    df['condition'] = conditions[0]
    if len(conditions.columns) > 1:
        df['[condition] (µM)'] = conditions[1]
    df.drop(columns =['Condition; Concentration (µM)'], inplace=True)
    
    return df


def _str2hours(datetime_string):
    
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


def wrangle_growthcurves(filename, merged=True):
    """Imports Tecan's default excel output for time-course data,
    parses out separate measurement types (if there are multiple).
    
    Parameters
    ----------
    filename : (string) filepath to the Tecan excel output
    merged : (boolean) determines whether output is merged dataframe 
        or a list of dataframes per measurment 

    Returns
    -------
    df_out : (DataFrame) tidy, all measurements combined
    df_list : (list of DataFrames) each tidied, one per
        measurement
    """
    
    # Import data, immediately drop any rows that have all NaN values.
    df = pd.read_excel(filename, sep=',', sheet_name=0, header=None)

    # The rows that indicate start/end of a measurement type
    rows = ['Kinetic read']
    
    # Make an iterable of those row numbers
    m_inds = df[df[df.columns[0]].isin(rows)].index
    
    # Instantiate list of size n per measurement type
    n_measurements = len(m_inds)
    df_list = [0] * n_measurements
    
    # Instantiate empty list to hold names of measurements
    measurement_list = []

    # Put dataframes into df_list
    # (one per measurement) and tidy them
    for i in range(n_measurements):
        
        # If there is a row above 'Kinetic read' store it 
        # as the name of the measurement type
        if (m_inds[i]-1) >= 0:
            m = str(df.iloc[m_inds[i]-1,0])
            measurement_list.append(m)
        else:
            measurement_list.append('value'+str(i))
        
        # Grab the relevant excel inds
        start_ind = m_inds[i]
        #size = m_inds[i+1]-m_inds[i]-2
        
        # Load in sub-df from excel file
        df_list[i] = pd.read_excel(filename, skiprows=start_ind)
        
        # Pull out the timepoints, in decimal hours,
        # from the STUPID excel datetime format
        # using custom _str2hours function
        hours = df_list[i]['Kinetic read'].astype('str').apply(_str2hours)
        
        # Add a time column in units of hours
        df_list[i]['Time [hr]'] = hours
        
        # Melt all the well identifier columns (e.g. A1, A2, etc.)
        df_list[i] = pd.melt(df_list[i],\
                                      id_vars=['Time [hr]', 
                                               'Kinetic read'])
        
        # Rename the new, ambiguously named columns
        df_list[i] = df_list[i].rename(
                                    columns={'variable':'well','value':m})
        
        # Delete Kinetic read column
        df_list[i] = df_list[i].drop('Kinetic read', axis=1)
        
        # Delete any rows that remain with NaN values
        df_list[i] = df_list[i].dropna(how='any')
    
    if merged == True:
        
        # loop over number of measurments to merge
        for i, m in enumerate(measurement_list):
            
            # instantiate new df on first loop
            if i == 0:
                df_out = df_list[i]
                
            # merge measurment m to the output dataframe
            if i > 0:
                mini_df = df_list[i][['well', 'Time [hr]', m]]
                df_out = df_out.merge(mini_df, on=['well','Time [hr]'])
    
        return df_out
    
    else:
        return tuple(df_list)
    
    
def import_growthcurves(data_file_path, legend_file_path):
    """Imports Tecan data with a legend and outputs a tidy dataframe 
    ready for EDA and viz.
    
    Parameters
    ----------
    legend_file_path : (string) filepath to the specific, filled-out 
        excel template
    data_file_path : (string) filepath to the Tecan excel output

    Returns
    -------
    df : (DataFrame) tidy, all measurements and annotations combined
    """
    
    df_data = wrangle_growthcurves(data_file_path)
    
    legend_df = plate_condmap(legend_file_path)
    
    return df_data.merge(legend_df, on='well')