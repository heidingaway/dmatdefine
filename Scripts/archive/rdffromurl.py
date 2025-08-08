import requests
import os
import rdflib

def download_file_with_session(url, file_path):
    """
    Downloads content from a URL to a local file, using browser-like headers.

    Args:
        url (str): The URL of the resource to download.
        file_path (str): The local path to save the file.

    Returns:
        bool: True if the download was successful, False otherwise.
    """
    # The exact headers from your successful browser request
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0',
        # IMPORTANT: Replace this cookie value with a fresh one if the script fails.
        'Cookie': 'ASPSESSIONIDAUTCADCT=MDHDFOOCDLGPCIFOOHNDICIG; ASPSESSIONIDQGABBCCS=EPEJFJGDDBLLMJPBKCFINNEB; ASPSESSIONIDAWTAAACR=CBPFJKHDEAECOOIKEFCLIILK; ASPSESSIONIDCGCRDADR=OKALKBIDMEDGEDFFDPLOJMMK; ASPSESSIONIDCUTBAACS=FLJDMAJDCAFMPOAIBLHDGAHN; ASPSESSIONIDAWADADDQ=PPINCFLDBIPHKLGCHHNJHFPL; ASPSESSIONIDQWCDCABR=EFKFELLDAMPCPPEGNDIGFELF; ASPSESSIONIDQGTACCCT=IAEFCBODIKCCMELFBFOCLJDG; ASPSESSIONIDSUSDCBBS=MKDBJJAAFJMEPJKKGMJAHILE; ASPSESSIONIDCURDCCDS=EHKFGBDAAGOECFGLMMEBGMKH; ASPSESSIONIDAWQABBBQ=BMNDBMLAOOELPLJLGHKJNCCM; ASPSESSIONIDAUDAAABS=CFIHECOAILANHPFDJNAPFGPB; ASPSESSIONIDQGSABDDQ=DENNFKOAMFBHMKCCPDINPLOO; ASPSESSIONIDQUAADCCS=HOEJNJABFKCHIHBBMFPMLDOF; ASPSESSIONIDSUDDDADQ=NDMNFEGBBNHPDIAPIHODNJIM; ASPSESSIONIDQWQDACBT=KPGJPEIBJCLHKMIOIIGLGKPP; ASPSESSIONIDAGCRCBDR=JHHJJPKBDMACGGANNJEMNNDG; ASPSESSIONIDSEDDDDDT=HBFBEAMBNPFDMCIFPKKPMPDB; ASPSESSIONIDSGRDCBCT=NBDBBBCCMPCKNAEBBNDFLFOF; ASPSESSIONIDCWBADBCR=PGFBHPDCFEINDCMDCPEHKAIJ; ASPSESSIONIDCWQBCCBQ=JDPNHGECFKNCAPHPBMDEPLGM; ASPSESSIONIDCEDRABAS=BKNNCDKCDOOIKCDIPKFKGIEP; ASPSESSIONIDSGCADDBT=GOKPGONCEDEJIAKIIPCMGOBE; ASPSESSIONIDQURCDBCT=ACDJIFOCLIGPJKDLHCBIOAAO; ASPSESSIONIDQWDBDBAQ=OPJPEDADANIOCKOOAGHKEMLH; ASPSESSIONIDCERBDDBQ=INFLBACDFPLGJDPNDIILGPBM; ASPSESSIONIDQGABDDDS=LAJJJMGDDKDAOLMKDOFPAMKK; ASPSESSIONIDQECAACDQ=BJDBJGHDEENCBNLLBPHGDGPF; ASPSESSIONIDAUSCDCBQ=AKNLMJJDJHIPKCHEDPDMNGPM; ASPSESSIONIDAGDRBABS=CICFPKMBFDOMOONEPEMAOOAM; ASPSESSIONIDCECSCBBR=JLDDAODAAEGICDFBFAKNMJGO; ASPSESSIONIDSGCSACBT=NBGPKHJBEKKKMFBJPAJBLCJJ; ASPSESSIONIDCGDRBCDS=NKOLJLDCJKNLNNAKLKKNIKKF; ASPSESSIONIDSGRRQADA=FFFDGJEDKIGMOGJMEFELMDGI; ASPSESSIONIDQGRTRCDA=HIBJGONDGHKKGABEANDLOGJB'
    }

    try:
        print(f"Attempting to download file from: {url}")
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        if response.history:
            print(f"\nWarning: The request was redirected from {response.history[0].url} to {response.url}")

        # Use 'wb' mode for writing bytes, then decode with 'utf-8-sig'
        # This ensures the BOM is handled correctly when reading later.
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"\nSuccessfully downloaded content to '{file_path}'")
        return True

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during download: {e}")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    rdf_url = "https://canada.multites.net/tsb/EAEAD1E6-7DD2-4997-BE7F-40BFB1CBE8A2/TSB20250610.rdf"
    
    # Define the output file path for the downloaded content
    downloaded_file_path = "/home/hide/Documents/Heidi2workspace/downloaded_content.txt"

    # Download the file
    if download_file_with_session(rdf_url, downloaded_file_path):
        print(f"Downloaded file size: {os.path.getsize(downloaded_file_path)} bytes.")
    else:
        print("Failed to download the RDF file.")