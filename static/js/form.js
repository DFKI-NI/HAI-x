function editValue(type, col, i) {
  save_button = document.getElementById(`save_btn_${type}`).disabled = false
  edit_id = `editable_${type}_${col}_${i}`
  cell = document.getElementById(edit_id);
  value = cell.innerHTML
  col = col.toLowerCase()
  if (col == 'type') {
    update = `<select class="dropdown form-control" id="edit_${type}_${col}_${i}">
                <option value="interest">interest</option>
                <option value="avoid" ${(value == "avoid") ? 'selected="selected"' : ''}>avoid</option>
              </select>`
  } else if (col == 'date') {
    update = `<input type="date" class="form-control" name="date" id="edit_${type}_${col}_${i}" value="${value}">`
  } else if (col == 'description') {
    update = `<input type="text" class="form-control" name="description" id="edit_${type}_${col}_${i}" value="${value}">`
  } else if (col == 'images') {
    update = `<input type="file" name="images" id="edit_${type}_${col}_${i}" accept="image/*" multiple />`
  }
  cell.innerHTML = update
}

function saveAll(url, type) {
  edited_cells = document.querySelectorAll(`[id^="edit_${type}"]`)
  update_dict = {}
  edited_cells.forEach(el => {
    data = el.id.split("_")
    col = data[2]
    index = data[3]
    val = el.value
    if (!update_dict.hasOwnProperty(index)) {
      update_dict[index] = {}
    }
    if (col == 'images') {
      images = ''
      files = Array.from(el.files)
      files.forEach(file => {
        images = images.concat(file.name, ';')
      })
      val = images
    }
    update_dict[index][col] = val
  });
  callServer(url, "POST", JSON.stringify(update_dict), () => {})
}

function checkAll(type) {
  source = document.getElementById(`all_checkbox_${type}`)
  checkboxes = Array.from(document.querySelectorAll(`[id^="checkbox_${type}"]`))
  checkboxes.forEach((checkbox, i) => {
    checkbox.checked = source.checked
  })
}

function deleteChecked(url, type) {
  checked_boxes = Array.from(document.querySelectorAll(`input[name=checkbox][id^="checkbox_${type}"]:checked`))
  to_delete = []
  checked_boxes.forEach((box, i) => {
    id = box.id.split("_")[2]
    to_delete.push(id)
  })
  callServer(url, "POST", JSON.stringify(to_delete), resetPage, checked_boxes)
}

function resetPage(checked_boxes) {
  checked_boxes.forEach((checkbox, i) => {
    checkbox.checked = false
  })
}

function updateTable(type, dropdown, show_more=null) {
  filter = show_more == null ? 0 : document.getElementById(show_more).value
  url = '/tables/get/info'
  params = {
    'type': type,
    'date': document.getElementById(dropdown).value,
    'filter': filter
  }
  callServer(url, "GET", jQuery.param(params), () => {})
}

function callServer(url, type, data, success, success_param=null) {
  $.ajax({
    url: url,
    type: type,
    contentType: 'application/json',
    data: data,
    success: function(response) {
      success(success_param)
      location.assign(response.redirect)
    },
    error: function(error) {
      console.log(error);
    }
  });
}