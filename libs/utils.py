import os
import tarfile
import base64
import shutil


TEMP_DIR = os.getcwd() + 'temp/'


def clear_temp_file():
    try:
        shutil.rmtree('temp')
    except FileNotFoundError:
        print('no temp file found..')
    finally:
        os.mkdir('temp')


def tar_file(directory: str):
    output_filename = directory + '.tar.gz'
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(directory, arcname=os.path.basename(directory))
        return tar


def base64_to_binary(name: str, base64_file: str) -> str:
    """
    This method reads a base64 file, saves it in the temporary folder and returns the absolute url
    :param name: name of the file
    :param base64_file: file's content
    :return: file's url
    """
    base64_file_bytes = base64_file.encode('utf-8')
    with open('temp' + name, 'wb') as file_to_save:
        decoded_image_data = base64.decodebytes(base64_file_bytes)
        file_to_save.write(decoded_image_data)
        file_to_save.close()
        return TEMP_DIR + name


def binary_to_base64(path: str) -> str:
    """
    Transforms a binary file to base64
    :param path: file's path
    :return: base code
    """
    with open(path, 'rb') as binary_file:
        binary_file_data = binary_file.read()
        base64_encoded_data = base64.b64encode(binary_file_data)
        base64_message = base64_encoded_data.decode('utf-8')
        return base64_message
