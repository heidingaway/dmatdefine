import pandas as pd 

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

print(dfic.columns)

# Export to CSV
dfic.to_csv('git\\dmatdefine\\reference data\\department_names.csv', index=False, encoding='utf-8-sig')