# Simple script that manages the creation of
# datastores in CKAN / HDX.

# path to download
PATH = 'data/temp.csv'

# dependencies
# import offset
import os
import csv
import json
import scraperwiki
import ckanapi
import urllib
import requests
import sys
import hashlib

# Collecting configuration variables
apikey = sys.argv[1]

# configuring the remote CKAN instance
ckan = ckanapi.RemoteCKAN('http://data.hdx.rwlabs.org', apikey=apikey)

# This is where the resources are declared. For now,
# they are declared as a Python list.
# This is a skeleton of a function that
# should fetch those schemas using other
# more refined methods.
def getResources(p):
    # resources = [
    #     {
    #         'resource_id': 'f48a3cf9-110e-4892-bedf-d4c1d725a7d1',
    #         'path': p,
    #         'schema': {
    #             "fields": [
    #                   { "id": "Indicator", "type": "text" },
    #                   { "id": "Country", "type": "text" },
    #                   { "id": "Date", "type": "timestamp"},
    #                   { "id": "value", "type": "float" }
    #             ]
    #         },
    #     }
    # ]

    resources = [
        {
            'resource_id': 'c244004f-9d47-4191-8f6e-7c765a08998e',
            'path': p,
            'schema': {
                "fields": [
                    { "id": "region", "type": "text" },
                    { "id": "numero_district", "type": "integer" },
                    { "id": "district", "type": "text" },
                    { "id": "variable_short_code", "type": "text" },
                    { "id": "variable", "type": "text" },
                    { "id": "value", "type": "float" }
                ]
            },
        }
    ]

    return resources


# Function to download a resource from CKAN.
def downloadResource(filename, resource_id):

    # querying
    url = 'https://data.hdx.rwlabs.org/api/action/resource_show?id=' + resource_id
    r = requests.get(url)
    doc = r.json()
    fileUrl = doc["result"]["url"]

    # downloading
    try:
        urllib.urlretrieve(fileUrl, filename)
    except:
        print 'There was an error downlaoding the file.'

# Function that checks for old SHA hash
# and stores as a SW variable the new hash
# if they differ. If this function returns true,
# then the datastore is created.
def checkHash(filename, first_run, resource_id):
    hasher = hashlib.sha1()
    with open(filename, 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
        new_hash = hasher.hexdigest()

    # checking if the files are identical or if
    # they have changed
    if first_run:
        scraperwiki.sqlite.save_var(resource_id, new_hash)
        new_data = False

    else:
        old_hash = scraperwiki.sqlite.get_var(resource_id)
        scraperwiki.sqlite.save_var(resource_id, new_hash)
        new_data = old_hash != new_hash

    # returning a boolean
    return new_data


def updateDatastore(filename, resource_id, resource):

    # Checking if there is new data
    update_data = checkHash(filename=filename,
                            first_run = False,
                            resource_id=resource_id)
    if (update_data == False):
        print "DataStore Status: No new data. Not updating datastore."
        return

    print "DataStore Status: New data. Updating datastore."

    def upload_data_to_datastore(ckan_resource_id, resource):
        # let's delete any existing data before we upload again
        try:
            ckan.action.datastore_delete(resource_id=ckan_resource_id, force=True)
        except:
            pass

        ckan.action.datastore_create(
                resource_id=ckan_resource_id,
                force=True,
                fields=resource['schema']['fields'],
                primary_key=resource['schema'].get('primary_key'))

        reader = csv.DictReader(open(resource['path']))
        rows = [ row for row in reader ]
        chunksize = 10000
        offset = 0
        print('Uploading data for file: %s' % resource['path'])
        while offset < len(rows):
            rowset = rows[offset:offset+chunksize]
            ckan.action.datastore_upsert(
                    resource_id=ckan_resource_id,
                    force=True,
                    method='insert',
                    records=rowset)
            offset += chunksize
            print('Update successful: %s' % offset)

    # running the upload function
    upload_data_to_datastore(resource_id, resource)

# wrapper call for all functions
def runEverything(p):
    # fetch the resources list
    resources = getResources(p)
    print '-------------------------------------'

    # iterating through the provided list of resources
    for i in range(0,len(resources)):
        resource = resources[i]  # getting the right resource
        resource_id = resource['resource_id']  # getting the resource_id
        print "Reading resource id: " + resource_id
        # downloadResource(p, resource_id)
        updateDatastore(p, resource_id, resource)
    print '-------------------------------------'
    print 'Done.'
    print '-------------------------------------'



# Error handler for running the entire script
try:
    runEverything(PATH)
    # if everything ok
    print "ScraperWiki Status: Everything seems to be just fine."
    scraperwiki.status('ok')

except Exception as e:
    print e
    scraperwiki.status('error', 'Creating datastore failed')
    os.system("mail -s 'SMART Survey: creating datastore failer.' luiscape@gmail.com")
