# python-export-to-csv
Export Entries, Assets and/or Org Users to CSV File(s)

* Selects entries based on content type and language.
* Exports all assets from a stack.
* Exports users on the org level. The user needs to have admin permission for the organization (to be allowed to read the org users).
* Exports users from all stacks and their roles in that stack. The user needs to have admin permission for the organization (to be able to get all the stacks), along with at least the Developer Role to each stack to be able to log out the user roles. The script will notify if access is missing from any stacks.

Exports using the Content Management API from Contentstack to a CSV file.

**Not officially supported by Contentstack**

## Prerequisites:
* Contentstack Account.
* Install Python 3 (Developed using Python 3.9.0 on Macbook).
* Install Python packages:
  * `pip install requests`
  * `pip install flatdict`
  * `pip install inquirer`
  * `pip install pandas`

## How to use:
* Run `python app.py` and answer questions that you get asked.
* If in trouble: Contact Oskar (oskar.eiriksson@contentstack.com)
* Exported CSV files go to a folder called `data/` (variables in config module)
