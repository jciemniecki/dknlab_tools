import pandas as pd

def plate_condmap(excel_file_path, delimiter=';'):
    """Imports a specific 96-well label layout from excel
    (found in dknlab_tools > templates)and outputs a tidy 
    dataframe of the labels.
    
    Parameters
    ----------
    excel_file_path : (string) filepath to the filled-out 
        excel template
    delimiter : (string) delimiter for parsing concentrations 
        from descriptors

    Returns
    -------
    df : (DataFrame) tidy, with index of well names (e.g., 'A4')
        and all the labels filled into the excel template.
     """
    
    # Read in condition map
    df = pd.read_excel(excel_file_path, dtype=str)
    
    # Melt column names (1, 2, etc) into their own df column
    df = df.melt(id_vars=['variable','row'], value_vars=[1,2,3,4,5,6,7,8], var_name='column')
    
    # Reformat into well identifier (A1, A2, etc)
    df['well'] = df['row'].apply(str) + df['column'].apply(str)
    df.drop(columns =["row", "column"], inplace = True)
    
    # Pivot to be tidy, then eliminate extra index names
    df = df.pivot(index='well', columns='variable')
    df.columns = df.columns.droplevel(0)
    df = df.rename_axis(columns=None)
    
    # Split media and condition columns
    media = df['Media; Concentration (mM)'].str.split(delimiter, n = 1, expand = True) 
    df['media'] = media[0]
    if len(media.columns) > 1:
        df['[media] (mM)'] = media[1]
    df.drop(columns =['Media; Concentration (mM)'], inplace = True)
    
    conditions = df['Conditions; Concentration (µM)'].str.split(delimiter, n = 1, expand = True) 
    df['conditions'] = conditions[0]
    if len(conditions.columns) > 1:
        df['[conditions] (µM)'] = conditions[1]
    df.drop(columns =['Conditions; Concentration (µM)'], inplace = True)
    
    return df