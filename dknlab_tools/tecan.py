import pandas as pd

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
    
    # Read in condition map
    df = pd.read_excel(filename, dtype=str)
    
    # Melt column names (1, 2, etc) into their own df column
    df = df.melt(id_vars=['variable','row'], 
                 value_vars=[1,2,3,4,5,6,7,8],
                 var_name='column')
    
    # Reformat into well identifier (A1, A2, etc)
    df['well'] = df['row'].apply(str) + df['column'].apply(str)
    df.drop(columns = ["row", "column"], inplace=True)
    
    # Pivot to be tidy, then eliminate extra index names
    df = df.pivot(index='well', columns='variable')
    df.columns = df.columns.droplevel(0)
    df = df.rename_axis(columns=None)
    
    # Split media and condition columns
    media = df['Media; Concentration (mM)'].str.split(delimiter, 
                                                      n=1, 
                                                      expand=True) 
    df['media'] = media[0]
    if len(media.columns) > 1:
        df['[media] (mM)'] = media[1]
    df.drop(columns =['Media; Concentration (mM)'], inplace=True)
    
    conditions = df['Conditions; Concentration (µM)'].str.split(delimiter, 
                                                                n=1, 
                                                                expand=True) 
    df['conditions'] = conditions[0]
    if len(conditions.columns) > 1:
        df['[conditions] (µM)'] = conditions[1]
    df.drop(columns =['Conditions; Concentration (µM)'], inplace=True)
    
    return df

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
    
    
    df = pd.read_excel(filename, sep=',', sheet_name=0)
    
    # The rows that indicate start/end of data
    rows = ['Cycle Nr.', 'End Time']
    
    # Make an iterable of the row numbers we're interested in
    inds = df[df[df.columns[0]].isin(rows)].index
    
    # Instantiate list of dfs per measurement type
    # Ignore last inds entry because it just marks the end of the data
    df_list = [0]*(len(inds)-1)
    measurement_list = []
    
    # Load dataframes into measurement list and tidy them
    for i in range(len(inds)-1):
        
        # Grab the name of the measurement type from the df
        m = str(df.iloc[inds[i]-1,0])
        measurement_list.append(m)
        
        # Grab the relevant excel inds
        start_ind = inds[i]+1
        size = inds[i+1]-inds[i]-2
        
        # Load in sub-df from excel file
        df_list[i] = pd.read_excel(filename,
                                            skiprows=start_ind,  
                                            nrows=size)
        
        # Drop NaN rows
        df_list[i] = df_list[i].dropna(how='all')
        
        # Add a time column in units of hours
        hours = (df_list[i]['Time [s]']/3600).round()
        df_list[i]['Time [hr]'] = hours
        
        # Melt all the well identifier columns (e.g. A1, A2, etc.)
        df_list[i] = pd.melt(df_list[i],\
                                      id_vars=['Time [hr]', 
                                               'Cycle Nr.', 
                                               'Time [s]', 
                                               'Temp. [°C]'])
        
        # Rename the new, ambiguously named columns
        df_list[i] = df_list[i].rename(
                                    columns={'variable':"well",                                                          'value':m})
    
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
    
def import_growthcurves(legend_file_path, data_file_path):
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
    
    legend_df = plate_condmap(legend_file_path)
    df_data = wrangle_growthcurves(data_file_path)
    df = df_data.merge(legend_df, on='well')
    
    return df