/**
 * HAIx Interface – Table interaction utilities
 * Handles inline editing, bulk selection, deletion, and AJAX table updates.
 */

function editValue(type, col, i) {
  const saveBtn = document.getElementById(`save_btn_${type}`);
  if (saveBtn) saveBtn.disabled = false;

  const editId = `editable_${type}_${col}_${i}`;
  const cell = document.getElementById(editId);
  if (!cell) return;

  const value = cell.innerHTML.trim();
  const colLower = col.toLowerCase();
  let update = '';

  if (colLower === 'type') {
    update = `<select class="form-select form-select-sm" id="edit_${type}_${col}_${i}">
                <option value="interest">interest</option>
                <option value="avoid" ${(value === 'avoid') ? 'selected="selected"' : ''}>avoid</option>
              </select>`;
  } else if (colLower === 'date') {
    update = `<input type="date" class="form-control form-control-sm" name="date" id="edit_${type}_${col}_${i}" value="${value}">`;
  } else if (colLower === 'description') {
    update = `<input type="text" class="form-control form-control-sm" name="description" id="edit_${type}_${col}_${i}" value="${value}">`;
  } else if (colLower === 'images') {
    update = `<input type="file" class="form-control form-control-sm" name="images" id="edit_${type}_${col}_${i}" accept="image/*" multiple>`;
  }

  cell.innerHTML = update;
}

function saveAll(url, type) {
  const editedCells = document.querySelectorAll(`[id^="edit_${type}"]`);
  const updateDict = {};

  editedCells.forEach(function(el) {
    const data = el.id.split('_');
    const col = data[2];
    const index = data[3];
    let val = el.value;

    if (!updateDict.hasOwnProperty(index)) {
      updateDict[index] = {};
    }

    if (col === 'images') {
      const files = Array.from(el.files);
      val = files.map(function(file) { return file.name; }).join(';');
    }

    updateDict[index][col] = val;
  });

  callServer(url, 'POST', JSON.stringify(updateDict), function() {});
}

function checkAll(type) {
  const source = document.getElementById(`all_checkbox_${type}`);
  const checkboxes = Array.from(document.querySelectorAll(`[id^="checkbox_${type}"]`));
  checkboxes.forEach(function(checkbox) {
    checkbox.checked = source.checked;
  });
}

function deleteChecked(url, type) {
  const checkedBoxes = Array.from(document.querySelectorAll(`input[name=checkbox][id^="checkbox_${type}"]:checked`));
  const toDelete = [];

  checkedBoxes.forEach(function(box) {
    // Extract the row index from the end of the checkbox id
    // Format: checkbox_<type>_<index> where type may contain underscores
    const parts = box.id.split('_');
    const id = parts[parts.length - 1];
    toDelete.push(id);
  });

  if (toDelete.length === 0) return;

  callServer(url, 'POST', JSON.stringify(toDelete), resetPage, checkedBoxes);
}

function resetPage(checkedBoxes) {
  if (!checkedBoxes) return;
  checkedBoxes.forEach(function(checkbox) {
    checkbox.checked = false;
  });
}

function updateTable(type, dropdown, showMore) {
  const filter = (typeof showMore === 'undefined' || showMore === null)
    ? 0
    : document.getElementById(showMore).value;
  const url = '/tables/get/info';
  const params = {
    'type': type,
    'date': document.getElementById(dropdown).value,
    'filter': filter
  };
  callServer(url, 'GET', jQuery.param(params), function() {});
}

function callServer(url, type, data, success, successParam) {
  $.ajax({
    url: url,
    type: type,
    contentType: 'application/json',
    data: data,
    success: function(response) {
      success(successParam);
      if (response && response.redirect) {
        location.assign(response.redirect);
      }
    },
    error: function(error) {
      console.error('Server request failed:', error);
    }
  });
}

function loadTrajData(type) {
  // Datum aus dem Dropdown holen
  const selectedDate = document.getElementById('load_traj_date').value;

  // Nur das Datum ans Backend schicken
  const payload = {
    date: selectedDate
  };

  // nutzt die vorhandene callServer-Funktion
  callServer('/traj/load', 'POST', JSON.stringify(payload), () => {});
}