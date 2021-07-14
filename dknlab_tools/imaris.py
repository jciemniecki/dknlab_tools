import os
import glob
import re
import pandas as pd


def import_agg_SYTO9_PI(folder_name, single_image=False):

    """
    args
    ----------------
    folder_name : (String) Folder name containing all the folders (one per image) 
                  of the raw imaris output. Function assumes user has multiple images 
                  that are being analyzed, and that each folder for an image 
                  has the name format "[imageidentifier]_Combined_Statistics".
    
    kwargs
    ----------------
    single_image : (Boolean) Pass True if only one image is being analyzed and the 
                   folder_name passed contains csv's with no folders.
    
    """

    if single_image==True:
        folderList = [folder_name]
    else:
        folderList = glob.glob(folder_name+'/*')
    
    Full_Results = pd.DataFrame()
    
    for i in folderList:
                
        zpos_file = glob.glob(i + '/*Position.csv')
        zpos = pd.read_csv(zpos_file[0], header=2, usecols=['Position Z'])
        zpos.rename(columns={'Position Z':'Position Z (µm)'}, inplace=True)
        vol_file = glob.glob(i + '/*Volume.csv')
        vol = pd.read_csv(vol_file[0], header=2, usecols=['Volume'])
        vol.rename(columns={'Volume':'Volume (µm^3)'}, inplace=True)
        dead_file = glob.glob(i + '/*Intensity_Mean_Ch=2_Img=1.csv')
        dead = pd.read_csv(dead_file[0], header=2, usecols=['Intensity Mean'])
        dead.rename(columns={'Intensity Mean':'PI Intensity (AU)'}, inplace=True)
        live_file = glob.glob(i + '/*Intensity_Mean_Ch=1_Img=1.csv')
        live = pd.read_csv(live_file[0], header=2, usecols=['Intensity Mean', 'ID'])
        live.rename(columns={'Intensity Mean':'SYTO-9 Intensity (AU)'}, inplace=True)
        
        result = pd.concat([zpos, vol, dead, live], axis=1)
        
        curFolderName = os.path.basename(i)
        curFolderName = curFolderName.split('_Combined_Statistics')[0]
        result['File'] = curFolderName
        
        #result.to_excel(curFolderName + '_concise.xls')
        Full_Results = Full_Results.append(result)
        
    # if FUll_Results['ID']
        
    return Full_Results