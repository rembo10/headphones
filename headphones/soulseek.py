from collections import defaultdict, namedtuple
import os
import time
import slskd_api
import headphones
from headphones import logger
from datetime import datetime, timedelta

Result = namedtuple('Result', ['title', 'size', 'user', 'provider', 'type', 'matches', 'bandwidth', 'hasFreeUploadSlot', 'queueLength', 'files', 'kind', 'url', 'folder'])

def initialize_soulseek_client():
    host = headphones.CONFIG.SOULSEEK_API_URL
    api_key = headphones.CONFIG.SOULSEEK_API_KEY
    try:
        return slskd_api.SlskdClient(host=host, api_key=api_key)
    except:
        logger.info("Something went wrong while connecting to the soulseek client")

    # Search logic, calling search and processing fucntions
def search(artist, album, year, num_tracks, losslessOnly):
    client = initialize_soulseek_client()
    
    # Stage 1: Search with artist, album, year, and num_tracks
    results = execute_search(client, artist, album, year, losslessOnly)
    processed_results = process_results(results, losslessOnly, num_tracks)
    if processed_results:
        return processed_results
    
    # Stage 2: If Stage 1 fails, search with artist, album, and num_tracks (excluding year)
    logger.debug("Soulseek search stage 1 did not meet criteria. Retrying without year...")
    results = execute_search(client, artist, album, None, losslessOnly)
    processed_results = process_results(results, losslessOnly, num_tracks)
    if processed_results:
        return processed_results
    
    # Stage 3: Final attempt, search only with artist and album
    logger.debug("Soulseek search stage 2 did not meet criteria. Final attempt with only artist and album.")
    results = execute_search(client, artist, album, None, losslessOnly)
    processed_results = process_results(results, losslessOnly, num_tracks, ignore_track_count=True)
    
    return processed_results

def execute_search(client, artist, album, year, losslessOnly):
    search_text = f"{artist} {album}"
    if year:
        search_text += f" {year}"
    if losslessOnly:
        search_text += " .flac"

    search_response = client.searches.search_text(searchText=search_text, filterResponses=True)
    search_id = search_response.get('id')
    
    # Wait for search completion and return response
    while not client.searches.state(id=search_id).get('isComplete'):
        time.sleep(2)
    
    return client.searches.search_responses(id=search_id)

# Processing the search result passed
def process_results(results, losslessOnly, num_tracks, ignore_track_count=False):
    valid_extensions = {'.flac'} if losslessOnly else {'.mp3', '.flac'}
    albums = defaultdict(lambda: {'files': [], 'user': None, 'hasFreeUploadSlot': None, 'queueLength': None, 'uploadSpeed': None})

    # Extract info from the api response and combine files at album level
    for result in results:
        user = result.get('username')
        hasFreeUploadSlot = result.get('hasFreeUploadSlot')
        queueLength = result.get('queueLength')
        uploadSpeed = result.get('uploadSpeed')

        # Only handle .mp3 and .flac
        for file in result.get('files', []):
            filename = file.get('filename')
            file_extension = os.path.splitext(filename)[1].lower()
            if file_extension in valid_extensions:
                album_directory = os.path.dirname(filename)
                albums[album_directory]['files'].append(file)

                # Update metadata only once per album_directory
                if albums[album_directory]['user'] is None:
                    albums[album_directory].update({
                        'user': user,
                        'hasFreeUploadSlot': hasFreeUploadSlot,
                        'queueLength': queueLength,
                        'uploadSpeed': uploadSpeed,
                    })

    # Filter albums based on num_tracks, add bunch of useful info to the compiled album
    final_results = []
    for directory, album_data in albums.items():
        if ignore_track_count or len(album_data['files']) == num_tracks:
            album_title = os.path.basename(directory)
            total_size = sum(file.get('size', 0) for file in album_data['files'])
            final_results.append(Result(
                title=album_title,
                size=int(total_size),
                user=album_data['user'],
                provider="soulseek",
                type="soulseek",
                matches=True,
                bandwidth=album_data['uploadSpeed'],
                hasFreeUploadSlot=album_data['hasFreeUploadSlot'],
                queueLength=album_data['queueLength'],
                files=album_data['files'],
                kind='soulseek',
                url='http://thisisnot.needed', # URL is needed in other parts of the program.
                folder=os.path.basename(directory)
            ))

    return final_results


def download(user, filelist):
    client = initialize_soulseek_client()
    client.transfers.enqueue(username=user, files=filelist)

def download_completed():
    client = initialize_soulseek_client()
    all_downloads = client.transfers.get_all_downloads(includeRemoved=False)
    album_completion_tracker = {}  # Tracks completion state of each album's songs
    album_errored_tracker = {}  # Tracks albums with errored downloads

    # Anything older than 24 hours will be canceled
    cutoff_time = datetime.now() - timedelta(hours=24)

    # Identify errored and completed albums
    for download in all_downloads:
        directories = download.get('directories', [])
        for directory in directories:
            album_part = directory.get('directory', '').split('\\')[-1]
            files = directory.get('files', [])
            for file_data in files:
                state = file_data.get('state', '')
                requested_at_str = file_data.get('requestedAt', '1900-01-01 00:00:00')
                requested_at = parse_datetime(requested_at_str)

                # Initialize or update album entry in trackers
                if album_part not in album_completion_tracker:
                    album_completion_tracker[album_part] = {'total': 0, 'completed': 0, 'errored': 0}
                if album_part not in album_errored_tracker:
                    album_errored_tracker[album_part] = False

                album_completion_tracker[album_part]['total'] += 1

                if 'Completed, Succeeded' in state:
                    album_completion_tracker[album_part]['completed'] += 1
                elif 'Completed, Errored' in state or requested_at < cutoff_time:
                    album_completion_tracker[album_part]['errored'] += 1
                    album_errored_tracker[album_part] = True  # Mark album as having errored downloads

    # Identify errored albums
    errored_albums = {album for album, errored in album_errored_tracker.items() if errored}

    # Cancel downloads for errored albums
    for download in all_downloads:
        directories = download.get('directories', [])
        for directory in directories:
            album_part = directory.get('directory', '').split('\\')[-1]
            files = directory.get('files', [])
            for file_data in files:
                if album_part in errored_albums:
                    # Extract 'id' and 'username' for each file to cancel the download
                    file_id = file_data.get('id', '')
                    username = file_data.get('username', '')
                    success = client.transfers.cancel_download(username, file_id)
                    if not success:
                        print(f"Failed to cancel download for file ID: {file_id}")

    # Clear completed/canceled/errored stuff from client downloads
    client.transfers.remove_completed_downloads()

    # Identify completed albums
    completed_albums = {album for album, counts in album_completion_tracker.items() if counts['total'] == counts['completed']}

    # Return both completed and errored albums
    return completed_albums, errored_albums


def parse_datetime(datetime_string):
    # Parse the datetime api response
    if '.' in datetime_string:
        datetime_string = datetime_string[:datetime_string.index('.')+7]
    return datetime.strptime(datetime_string, '%Y-%m-%dT%H:%M:%S.%f')