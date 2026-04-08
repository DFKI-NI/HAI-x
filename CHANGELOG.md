# Changelog

## Unreleased (2026-03-13)

### Fixes

- Fix: synchronise the video and click on the map to set the video time.
    
- Fix: incorrect container for density_based_clustering was used.
    
- Fix(#60): store bathymetry points in interface.bathymetry.
    
  **refactor:** remove deprecated lake_bathymetry table

### Other

- The data segment was modified.
    
- Merge remote-tracking branch 'origin/Junie-interface-polish' into Junie-interface-polish.
    
- The data segment was modified.
    
- View of possible dates in selection box in evaluation view.
    
- Merge remote-tracking branch 'origin/Junie-interface-polish' into Junie-interface-polish.
    
- Feat(path, traj, area): add summary views and fix delete refresh.
    
  Simplified Path and Trajectory tables by introducing summary views and fixing
  the issue where the Area delete action did not refresh the table.

  - Trajectory now shows one row per run instead of hundreds of datapoints.
  - Planned Path now has a summary tab plus a raw tab for point editing.
  - Delete logic updated (by date, path_id, or idx depending on view).

  Closes #50
  Closes #54
- Server is not crashing due to large forms.
    
- Junie changes: updated bathymetry, sentinel-2, clustered aoi, and path planning container. moved some logic from python to javascript for submitting requests. new design with css.
    
## 0.19 (2026-02-04)

### Other

- Resolve "Automated data flow from sensor box to the interface".
    
## 0.18.12 (2026-01-28)

### Updates

- Changed the path to the videos.
    
## 0.18.10 (2026-01-19)

## 0.18.11 (2026-01-19)

## 0.18.8 (2026-01-19)

## 0.18.9 (2026-01-19)

### Other

- Adjusted the .env.
    
## 0.18.7 (2026-01-19)

### Other

- Evaluation is now available.
    
- Evaluation is now available.
    
## 0.18.6 (2026-01-19)

### Other

- Evaluation is now available.
    
## 0.18.5 (2026-01-19)

### Other

- Evaluation is now available.
    
## 0.18.2 (2026-01-19)

## 0.18.3 (2026-01-19)

## 0.18.4 (2026-01-19)

### Other

- Evaluation is now available.
    
## 0.18.1 (2026-01-19)

### Other

- Evaluation is now available.
    
## 0.18 (2026-01-19)

### Other

- Evaluation is now available.
    
- Evaluation is now available.
    
## 0.17.12 (2025-10-29)

### Other

- Configuration Page.
    
## 0.17.10 (2025-09-02)

## 0.17.11 (2025-09-02)

## 0.17.5 (2025-09-02)

## 0.17.6 (2025-09-02)

## 0.17.7 (2025-09-02)

## 0.17.8 (2025-09-02)

## 0.17.9 (2025-09-02)

### Fixes

- Fixed bug in new areas.
    
- Fixed bug in new areas.
    
- Fixed bug in new areas.
    
- Fixed bug in new areas.
    
- Fixed bug in new areas.
    
- Fixed bug in new areas.
    
- Fixed bug in new areas.
    
- Fixed bug in new areas.
    
- Fixed bug in new areas.
    
### New

- New version.
    
- New version.
    
- Added dates as text to the get area. currently only for the maschsee.
    
### Other

- Merged main into branch.
    
- Merged main into branch.
    
## 0.17.2 (2025-08-07)

## 0.17.3 (2025-08-07)

## 0.17.4 (2025-08-07)

### New

- New version.
    
### Other

- Merge remote-tracking branch 'origin/main'.
    
## 0.17.1 (2025-08-07)

### New

- Added 'cd interface'.
    
## 0.17 (2025-08-07)

### New

- New version.
    
### Other

- Merge remote-tracking branch 'origin/main'.
    
- Aois can now generated automatically with the service.
    
### Updates

- Update file .gitlab-ci.yml.
    
- Update .gitlab-ci.yml file.
    
## 0.16.6 (2025-08-06)

### Other

- Merged main into branch.
    
- Edit compose.yaml.
    
- Edit compose.yaml.
    
- Visualization of apa index for a given date.
    
### Updates

- Update .gitlab-ci.yml file.
    
## 0.16.5 (2025-07-23)

### Updates

- Changed sentinelhub variables.
    
- Update file compose.yaml.
    
- Changed pull policy for estimate_areas_of_interest service in docker compose.
    
## 0.16.4 (2025-07-23)

### Updates

- Changed container version for apa-index.
    
## 0.16.3 (2025-07-23)

### Fixes

- Fixed typo in compose.
    
## 0.16.1 (2025-07-23)

## 0.16.2 (2025-07-23)

### Other

- Small change in variables.py.
    
- Small changes in language variables and planned paths show now the length.
    
### Updates

- Changed compose-file to load env variables in docker.
    
## 0.16 (2025-07-14)

### New

- Added pull credentials.
    
- Added git pull to gitlab-ci.
    
- Added compose file to gitlab-ci.
    
### Other

- Small changes in language variables and planned paths show now the length.
    
- Corrected pull commands on hai-x server.
    
- Small changes in language variables and planned paths show now the length.
    
- Small changes in language variables and planned paths show now the length.
    
- Explainability Framework Integration with SONAR Detections.
    
### Updates

- Update .gitlab-ci.yml file.
    
- Update .gitlab-ci.yml file.
    
## 0.15 (2025-06-18)

### New

- New version.
    
### Other

- Merge remote-tracking branch 'origin/main'.
    
### Updates

- Deleted the mount command.
    
## 0.14 (2025-06-18)

### New

- New version.
    
- Added the clustering part of aoi based on apa.
    
### Other

- Language change is now not a button anymore.
    
- Language change is now not a button anymore.
    
- Edited docker compose for getting sentinel data.
    
- Merged master into branch.
    
- Merge remote-tracking branch 'origin/main' into 23-adding-information-from-the-satellite-data.
    
- Path Planning is now with a real algorithm.
    
- Path Planning is now with a real algorithm.
    
- Path Planning is now with a real algorithm.
    
- Merged main into branch.
    
- Path Planning is now with a real algorithm.
    
- Merge remote-tracking branch 'origin/main'.
    
- Edit compose.yaml.
    
- Path Planning is now with a real algorithm.
    
- Merge remote-tracking branch 'origin/main'.
    
- Edit README.md.
    
- Some changes.
    
- Some changes.
    
- Some changes.
    
- Merge remote-tracking branch 'origin/main'.
    
- Edit README.md.
    
- Some changes.
    
- Some changes.
    
- Some changes.
    
- Some changes.
    
- Merge remote-tracking branch 'origin/main'.
    
- Some changes.
    
- Merge remote-tracking branch 'origin/main'.
    
- Edit .gitlab-ci.yml.
    
- Some changes.
    
- Data retrieval from sentinelhub tested in docker. Documentation is in the Readme.md.
    
### Updates

- Removed the submodules etc.
    
- Update .gitlab-ci.yml file, videos are now mounted from the synology fileserver.
    
## 0.13 (2025-04-11)

### Fixes

- Fix issue #22.
    
### New

- Add path in map [newarea.html].
    
### Other

- Merge remote-tracking branch 'origin/main'.
    
- Edit README.md.
    
- Some changes.
    
- Edit requirements.txt.
    
- Resolve "replace csv with database".
    
- Edit README.md.
    
- Edit README.md.
    
- Cleaning.
    
- Cleaning code.
    
- Deleting functionality for trajectory.
    
- Filtering and dropdown error fixes.
    
- Show more rows functionality.
    
- Cleand code.
    
- Display correct table on dropdown change.
    
- Merge resolve.
    
- Load table on dropdown change.
    
## 0.12 (2024-11-18)

### Fixes

- Fixing save and delete issues.
    
### New

- Added cmd to dockerfile.
    
- New version.
    
- Added map in new area - first version.
    
### Other

- Cleand code and files.
    
- Cleand unused code.
    
- Switched from dash map to folium to draw polygones.
    
- Path tab with functionality.
    
- Renaming column.
    
### Updates

- Update .gitlab-ci.yml file.
    
- Update requirements.
    
- Update changelog.
    
- Removed input field for coordinates.
    
- Update changelog.
    
- Update .gitlab-ci.yml file.
    

## 0.11 (2024-11-07)

### Fixes

- Fixing page refresh.
    
- Fixing page refresh.
    
### New

- New version.
    
- Added latitude and longitude to video info csv and script to create videos and info csv.
    
- Adding more fields to path generation.
    
- Add time.
    
- Adding dates for clarity.
    
### Other

- Clean unused code.
    
- Clean code.
    
- Updating images.
    
- Double click cells.
    
- Initial table.
    
- Disable approval.
    
- Multiple dates.
    
- Show gradient trajectories.
    
- Clean unused code.
    
- Show interest/avoid areas.
    
### Updates

- Update .gitlab-ci.yml file.
    
- Update .gitlab-ci.yml file.
    
- Update .gitlab-ci.yml file.
    
- Update .gitlab-ci.yml file.
    
- Update .gitlab-ci.yml file.
    
- Update .gitlab-ci.yml file.
    
- Update .gitlab-ci.yml file.
    
- Update .gitlab-ci.yml file, yet unfinished.
    
- Update: display of the entire video instead of the sections.
    
- Delete rows.
    
- Update table and save.
    
- Remove print statements.
    
## 0.10 (2024-10-16)

### Other

- Version number is now string.
    
### Updates

- Update README.md.
    
- Changelog display.
    

## 1.0 (2024-10-15)

### New

- Add changelog.
    
- Add all paths to map.
    
### Other

- Cleaning code.
    
- Showing error message.
    
- Approve some paths.
    
- Parallel view of rgb and infra video added.
    
- Displaying map.
    
- Displaying correctly.
    
- Approve paths on button click.
    
- Merge conflict.
    
- Include only date, show fig w/ dummy code.
    
- Neues req.
    
### Updates

- Update layout.
    
- Changed the README.md.
    
- Update README.md.
    
- Update README.md.
    
- Changed the README.md.
    
- Changed run command in README.md.
    
- Deleted videos from the git.
    
- Deleted videos from the git.
    
- Changed requirements.
    
- Changed requirements.
    
- Changed requirements.
    
- Changed requirements.
    
- Changed requirements.
    
## 0.9 (2024-09-12)

### Fixes

- Fixing navbar.
    
- Fixing small bugs.
    
### New

- New version.
    
- New path planning.
    
- New path planning.
    
- Adding multiple paths to form.
    
- Add generate path page.
    
- New video util file.
    
- New dockerfile.
    
- New data.
    
- New dockerfile.
    
- New layout with bootstrap.
    
- Adding version.
    
- New layout with bootstrap.
    
### Other

- Collapsing menu.
    
- Small changes in design.
    
- Logic for multiple paths in form.
    
- Calling script on form submit.
    
- Show generate path form.
    
- Videos for another day.
    
- Videos for another day.
    
- Small changes on the layout.
    
- Small changes on the layout.
    
- Merge remote-tracking branch 'origin/main'.
    
- Merge remote-tracking branch 'origin/8-integrate-jinja-and-html-together-with-dash' into 8-integrate-jinja-and-html-together-with-dash.
    
- Cleaning up unused file.
    
- Removing unused imports.
    
- Removing pycache files.
    
- Display new area and path.
    
- Include routes, variables, utils.
    
- Merge remote-tracking branch 'origin/main'.
    
- Convert to jinja templates.
    
- Show has_video on hover.
    
- Showing info on date dropdown.
    
- Has image on hover.
    
### Updates

- Update file dockerfile.
    
## 0.8 (2024-08-19)

### Fixes

- Fixing bug.
    
### Other

- Start and stop have now color and text.
    
- Break.
    
- Removing print.
    
- Showing start and stop.
    
- In progress adding scattermap.
    
### Updates

- Update file app.py.
    
- Remove points on click.
    
- Changed the video codec.
    
- Changed the video codec.
    
- Changed the video codec.
    
## 0.7 (2024-08-08)

### Other

- SSL now.
    
- Bug fixing.
    
- Merge conflict.
    
- Spacing around buttons.
    
- Merge resolve.
    
- Bug fixing.
    
- Dcc.Store issue.
    
### Updates

- Delete paths and points.
    
- Remove prints.
    
## 0.6 (2024-07-30)

### New

- New release.
    
### Other

- Merge remote-tracking branch 'origin/main'.
    
- The movie was split into parts.
    
- The movie was split into parts.
    
- The movie was split into parts.
    
- Bug fixing.
    
- Bug fixing.
    
- Video integration.
    
- Video integration.
    
### Updates

- Update file requirements.txt.
    
- Update file requirements.txt.
    
- Update file requirements.txt.
    
## 0.5 (2024-07-26)

### New

- Adding messaging, keeping files up to date.
    
### Other

- Video integration.
    
- Video integration.
    
- Video integration.
    
## 0.4 (2024-07-24)

### Other

- Merged branches.
    
- Merge fix.
    
- Removing data on delete.
    
- Display delete button, call function.
    
### Updates

- Updates to UI.
    
- Changed the names for better understanding.
    
- Changed the docker procedure.
    
## 0.3 (2024-07-23)

### Other

- Next release.
    
- The version number is now displayed on the website.
    
- Destroyed and repaired the picture upload.
    
## 0.2 (2024-07-22)

### Other

- The version number is now displayed on the website.
    
- Optimized the dropdown menu.
    
## 0.1 (2024-07-22)

### Fixes

- Fixed issue in object return.
    
### New

- Adding description to hover tool.
    
- Add README.md.
    
### Other

- Uploading pictures.
    
- Formatting form and adding filenames to data file.
    
- Optimized the dropdown menu.
    
- Height adjustment.
    
- Adjusting image display.
    
- Showing images.
    
- Optimized the dropdown menu.
    
- Optimized the dropdown menu.
    
- Optimized the dropdown menu.
    
- Optimized the dropdown menu.
    
- Optimized the dropdown menu.
    
- More than one path per day is now possible.
    
- Merge remote-tracking branch 'origin/main'.
    
  # Conflicts:
  #	data/geo.json
- Merge conflict.
    
- Optimized.
    
- Merge remote-tracking branch 'origin/main'.
    
  # Conflicts:
  #	app.py
- Showing coordinates on area click.
    
- Merge conflict.
    
- Work in progress showing coordinates on click.
    
- Implemented the possibility to create areas.
    
- Included trajectory of the boat.
    
- Implemented the possibility to create areas.
    
- Implemented the possibility to create areas.
    
- Created a Dockerfile.
    
- Displaying description on hover.
    
- Areas are now dynamic.
    
- Areas are now dynamic.
    
- A grid was created and implemented.
    
- A first map in plotly dash.
    
- Imported plotly dash.
    
- Imported plotly dash.
    
- Imported plotly dash.
    
- Some changes for deleting, accepting and declining rectangles.
    
- Saving method improved.
    
- Saving method.
    
- Upload Logo.
    
- Removing print statements.
    
- Removing duplicate code.
    
- In progress - displaying areas from dataframe.
    
- Initial.
    
- Initial.
    
- Initial commit.
    
### Updates

- Rename images if duplicate.
    
- Changed data structure.
    
- Changed data structure.
    
- Changed data structure.
    
- Changed data structure.
    
- Changed the Readme.
    
- Change to flask.
    
- Change to flask.
    
- Change to flask.
    
- Change to flask.
    
- Change to flask.
    
- Change to flask.
    

