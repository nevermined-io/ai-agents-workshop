import os
from pinatapy import PinataPy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PINATA_API_KEY = os.getenv('PINATA_API_KEY')
PINATA_SECRET_API_KEY = os.getenv('PINATA_API_SECRET')

# Connect to Pinata
pinata = PinataPy(PINATA_API_KEY, PINATA_SECRET_API_KEY)

IPFS_PUBLIC_GATEWAY = "https://gateway.pinata.cloud/ipfs/{CID}"


class IPFSHelper:
    """
    Helper class for interacting with Pinata and uploading files to IPFS.
    """

    @staticmethod
    async def upload_file_to_ipfs(filename="file.mp3"):
        """
        Uploads an file to IPFS through Pinata.

        Args:
            filename (str): Name to assign the uploaded file.

        Returns:
            str: The CID (content identifier) of the uploaded file.
        """

        try:
            # Upload the file to Pinata
            result = pinata.pin_file_to_ipfs(filename, save_absolute_paths=False)
            cid = result['IpfsHash']

            return cid
        except Exception as e:
            raise Exception(f"Failed to upload file to Pinata: {e}")
        finally:
            # Delete the temporary file
            if os.path.exists(filename):
                os.remove(filename)

    @staticmethod
    def get_ipfs_url(cid):
        """
        Constructs the public URL for accessing an IPFS file.

        Args:
            cid (str): The CID of the content.

        Returns:
            str: The public IPFS URL.
        """
        return IPFS_PUBLIC_GATEWAY.replace("{CID}", cid)
