import pandas as pd 
import numpy as np
import re

# Pull latest department names & prepare the dataframes 
concordance = "https://open.canada.ca/data/dataset/57180b36-3428-4a7f-afe3-2161a6b44ec5/resource/3faaafb4-00e2-4303-947d-ac786b62559f/download/gc_concordance.csv"

org_info = "https://open.canada.ca/data/dataset/57180b36-3428-4a7f-afe3-2161a6b44ec5/resource/cb5b5566-f599-4d12-abae-8279a0230928/download/gc_org_info.csv"

dfc = pd.read_csv(concordance)

dfi = pd.read_csv(org_info)
dfi['gc_orgID'] = dfi['gc_orgID'].astype(str)
dfc = dfc.drop(columns=["harmonized_name", 'nom_harmonisé', 'abbreviation', 'abreviation'])
dfc['gc_orgID'] = dfc['gc_orgID'].astype(str)

# create a single dataset with department information 

dfic = pd.merge(dfi , dfc, on = "gc_orgID")

# create a smaller reference table of department abbreviations and names
df = pd.DataFrame(dfic, columns = ['abbreviation', 'abreviation', 'gc_orgID' , 'preferred_name', 'nom_préféré'])


# Pull latest Partner data
mou_file = "mou\\Test  for Collection Email Draft - Current and prospective partner data - Tracker - Copy.xlsx"
dfm = pd.read_excel(mou_file, sheet_name="Current partners")
dfm = dfm.rename(columns={'Partner \nLast updated: \nFeb 12, 2025':'partner'})

# standardize partner abbreviations and replace values in 'partner abbreviation' with standardized ones
correctedpartners = {'ISC/CIRNAC': 'ISC', 'STC': 'StatCan', 'Total participation (partner and non-partner)': ''}

dfm['partner_corrected'] = dfm['partner'].replace(correctedpartners)
dfm = pd.merge(dfm, df, how = 'left', left_on= 'partner_corrected', right_on='abbreviation')

# find all the MOU partners with remaining abbreviation issues
mou = pd.DataFrame(dfm , columns =['partner', 'partner_corrected', 'abbreviation', 'gc_orgID'])

mouclean = pd.merge(mou , df , how = 'left' , left_on= 'partner', right_on= 'abbreviation')

# missingabbrev = mouclean[mouclean['abbreviation'].isna()]

# print(missingabbrev)


# explore other columns in partner data to see what should be pulled

moucontacts = pd.DataFrame(dfm, columns= ['partner', 'partner_corrected', 'Members Name(s)', 'Members/Participant Email address(es)'])


def clean_column(text_series):
    return text_series.str.replace(r"\s*\n\s*", ";", regex=True)


# Apply to multiple columns
columns_to_clean = ['Members Name(s)', 'Members/Participant Email address(es)']
moucontacts[columns_to_clean] = moucontacts[columns_to_clean].apply(lambda col: clean_column(col))



# Step 1: Split by semicolon into member_1, member_2, ...
mou_split = moucontacts['Members Name(s)'].str.split(";", expand=True)
mou_split.columns = [f'member_{i+1}' for i in range(mou_split.shape[1])]


# Step 2: Keep only part1 (e.g., last names)
final_moucontact = pd.DataFrame()
for col in mou_split.columns:
    part1 = mou_split[col].str.split(",", expand=True)[0]
    part2 = mou_split[col].str.split(",", expand=True)[1]
    final_moucontact[f'{col}_name'] = part1
    final_moucontact[f'{col}_title'] = part2


# Step 3: Split member_i_name into first and last name
name_parts_df = pd.DataFrame()
for col in final_moucontact.columns:
    if col.endswith('_name'):
        name_parts = final_moucontact[col].str.strip().str.split(" ", n=1, expand=True)
        name_parts.columns = [f'{col}_first', f'{col}_last']
        name_parts_df = pd.concat([name_parts_df, name_parts], axis=1)


# Step 1: Split by semicolon into member_1, member_2, ...
mouemail_split = moucontacts['Members/Participant Email address(es)'].str.split(";", expand=True)
mouemail_split.columns = [f'member_{i+1}_email' for i in range(mouemail_split.shape[1])]


final_moucontact = pd.concat([moucontacts,name_parts_df, mouemail_split], axis=1)
final_moucontact = final_moucontact.drop(columns= columns_to_clean)
final_moucontact = final_moucontact[sorted(final_moucontact.columns)]


# join MOU clean with clean contact list

merged_df = pd.merge(mouclean, final_moucontact, how = 'left', on='partner', suffixes=('', '_dup'))

# Drop duplicated columns (those with '_dup' suffix)
merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith('_dup')]

partnerdata = pd.merge(merged_df, dfm, how = 'right', on='partner_corrected', suffixes=('', '_dup'))
# Drop duplicated columns (those with '_dup' suffix)
partnerdata = partnerdata.loc[:, ~partnerdata.columns.str.endswith('_dup')]
partnerdata = partnerdata.drop(columns="partner_corrected")
partnerdata = partnerdata.rename(columns={"abbreviation":"abbrev_en", "abreviation":"abbrev_fr"})
partnerdata.replace('✓', 'Yes', inplace=True)


# Define the desired order
desired_order = ['gc_orgID', 'partner', 'Contribution', 'Partner since','MOU signed', 'Payment Received', 'abbrev_en', 'abbrev_fr', 'preferred_name',
       'nom_préféré','member_1_email', 'member_1_name_first',
       'member_1_name_last', 'member_2_email', 'member_2_name_first',
       'member_2_name_last', 'member_3_email', 'member_3_name_first',
       'member_3_name_last', 'member_4_email',] # Add your preferred columns here
#remaining_cols = [col for col in partnerdata.columns if col not in desired_order]

# Reorder the DataFrame
#partnerdata = partnerdata[desired_order + remaining_cols]

export = partnerdata[desired_order]
print(export.columns)
# Export to CSV
export.to_csv('partnerdata.csv', index=False, encoding='utf-8-sig')
