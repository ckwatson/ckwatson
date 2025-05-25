// JS fixes START
$.urlParam = function (name) {
  const results = new RegExp('[\?&]' + name + '=([^&#]*)').exec(window.location.href)
  if (!results) {
    return ''
  }
  return results[1] || ''
}
if (typeof (String.prototype.trim) === 'undefined') {
  String.prototype.trim = function () {
    return String(this).replace(/^\s+|\s+$/g, '')
  }
}
if (!Object.keys) {
  Object.keys = function (o) {
    if (o !== Object(o)) throw new TypeError('Object.keys called on non-object')
    const ret = []
    let p
    for (p in o) { if (Object.prototype.hasOwnProperty.call(o, p)) ret.push(p) }
    return ret
  }
}

dict_reverse = function (obj) {
  const new_obj = {}
  for (const prop in obj) {
    if (obj.hasOwnProperty(prop)) {
      new_obj[obj[prop]] = prop
    }
  }
  return new_obj
}
// JS fixes END

currentViewType = 'info'

print = function (content) {
  $('#console').append('<p>' + content + '</p>')
}
const emptyElementaryReaction = $(`
                    <tr class="elementaryReaction" draggable="true">
                        <td>
                            <input type="checkbox" class="form-check-input" checked>
                        </td>
                        <td>
                            <select class="form-control">
                                <option value=""></option>
                            </select>
                        </td>
                        <td>
                            +
                        </td>
                        <td>
                            <select class="form-control">
                                <option value=""></option>
                            </select>
                        </td>
                        <td>
                            =
                        </td>
                        <td>
                            <select class="form-control">
                                <option value=""></option>
                            </select>
                        </td>
                        <td>
                            +
                        </td>
                        <td>
                            <select class="form-control">
                                <option value=""></option>
                            </select>
                        </td>
                        <td>
                            <button type="submit" class="btn btn-danger btn-sm removeReaction">
                                Remove
                            </button>
                        </td>
                    </tr>
`)
const hasEmptyElementaryReaction = true
// functions for checking mass balances of elementary reactions:
checkOverallBalance = function () {
  if ($('#elementaryReactionsTbody>tr.bg-danger-subtle').length == 0 && $('#elementaryReactionsTbody > tr.bg-success-subtle').length > 0) {
    $('#plotButton').removeClass('disabled').prop('disabled', false)
  } else {
    $('#plotButton').addClass('disabled').prop('disabled', true)
  }
}
checkBalance = function (thisRow) {
  cells = $('td>select', thisRow).toArray()
  atomsArray = {}
  for (var i in cells) {
    // console.log(i,cells[i]);
    species = cells[i].value
    if (species == '') continue // skip empty species.
    atoms = species.match(/([A-Z][a-z]?)(\d*)/g)
    for (const j in atoms) {
      atom = atoms[j]
      number = parseInt(atom.replace(/[^\d]/g, ''), 10) || 1
      element = atom.replace(/\d*/g, '')
      if (i < 2) { // reactant
        atomsArray[element] = (atomsArray[element] || 0) + number
      } else { // product
        atomsArray[element] = (atomsArray[element] || 0) - number
      };
    };
  }
  if ($.isEmptyObject(atomsArray)) { // user emptied the reaction
    thisRow.removeClass('bg-danger-subtle')
    thisRow.removeClass('bg-success-subtle')
  } else {
    let ifBalanced = true
    for (var i in atomsArray) {
      if (atomsArray[i] != 0) {
        ifBalanced = false
        break
      }
    }
    if (ifBalanced) {
      thisRow.removeClass('bg-danger-subtle')
      thisRow.addClass('bg-success-subtle')
    } else {
      thisRow.addClass('bg-danger-subtle')
      thisRow.removeClass('bg-success-subtle')
    }
    // console.log(ifBalanced, atomsArray);
    return ifBalanced
  }
}
// Behavior of the rows of elementary reactions:
onSelectChange = function (e) {
  // console.log(this.value);
  const thisRow = $($(this).parent().parent().get(0))
  // Check mass balance
  checkBalance(thisRow)
  checkOverallBalance()
}
removeElementaryReaction = function (e) {
  $(this).parent().parent().remove()
  checkOverallBalance()
}
addElementaryReaction = function () {
  thisElementaryReaction = emptyElementaryReaction.clone()
  $('#elementaryReactionsTbody').append(thisElementaryReaction)
  cells = thisElementaryReaction.children('td') // just a short-hand.
  cells.children('button.removeReaction').click(removeElementaryReaction)
  cells.children('select').change(onSelectChange)
  $('td>select', thisElementaryReaction).on('dragover', function (ev) {
    ev.originalEvent.preventDefault()
  })
  $('td>select', thisElementaryReaction).on('drop', function (ev) {
    ev.originalEvent.preventDefault()
    const data = ev.originalEvent.dataTransfer.getData('species')
    if (data != undefined && data != '') {
      $(this).val(data)
      $(this).change()
    };
  })
}
// Behavior of the rows of elementary reactions -- END
const serverEventListeners = {}
function plot () {
  // Get reactions
  var reactions = $('#elementaryReactionsTbody>tr.bg-success-subtle').map(function () {
    return [$('td>select', this).map(function () {
      return this.value
    }).toArray()]
  })
  // Get temperature
  const temperature = parseFloat(document.getElementById('reactionTemperature').value, 10)
  // Get conditions
  var conditions = $('#conditionTbody > tr.reactant').map(function () {
    const name = $('td.species', this).text().trim()
    const amount = parseFloat($('td>input.amount', this).val())
    const temperature = parseFloat($('td>input.temperature', this).val())
    return { name, amount, temperature }
  })
  // make jobID. this should better be unique across all users and all calls.
  const d = new Date()
  var reactions = $.makeArray(reactions).sort()
  var conditions = $.makeArray(conditions).sort()
  const solutionID = md5(JSON.stringify(reactions))
  const conditionID = md5(JSON.stringify(conditions))
  const jobID = ip + '_' + conditionID + '_' + temperature.toString() + '_' + solutionID + '_' + d.getTime().toString() // $('#result_nav > li').length + 1;
  if ($(`#${jobID}`).length > 0) {
    $(`#${jobID}_nav`).tab('show')
  } else {
    const $btn = $(this)
    $btn.prop('disabled', true).text('Loading...')
    parameters = {
      puzzle: puzzleName,
      reactions,
      temperature,
      conditions,
      jobID,
      solutionID,
      conditionID
    }
    // Create a new panel for this job. It will contain the plots and the logs in three different tabs:
    const thisResultPanel = $(`
      <div class="tab-pane" id="${jobID}" role="tabpanel">
        <div class="view_individual" style="display:none"></div>
        <div class="view_combined" style="display:none"></div>
        <pre class="view_info language-python"></pre>
        <div class="card-footer"></div>
      </div>`)
    thisResultPanel.appendTo('#result_panels')
    console.log('Adding new tab pane for this job:', thisResultPanel)

    // Immediately switch current view setting
    currentViewType = 'info'
    $('#button_to_view_info').click()

    // Add a new tab for this job:
    const thisResultNavPage = $(`
      <li class="nav-item" role="presentation">
        <button class="nav-link" id="${jobID}_nav" data-bs-toggle="tab" data-bs-target="#${jobID}" type="button" role="tab">Plotting...</button>
      </li>`)
    thisResultNavPage.appendTo('#result_nav')
    console.log('Adding new tab button for this job:', thisResultNavPage)
    $(`#${jobID}_nav`).tab('show')

    // Start listening to the server about how it gonna be doing:
    const source = new EventSource('/stream?channel=' + jobID) // See: http://flask-sse.readthedocs.io/en/latest/advanced.html#channels
    serverEventListeners[jobID] = source
    source.jobID = jobID
    /* source.onopen = function() {
            console.log('EventSource opened:',this);
        }; */
    source.onmessage = function (event) {
      /* console.log(event.data);
            console.log(this); */
      const data = JSON.parse(event.data)
      const $infoPanel = $(`#${this.jobID} .view_info`)
      $infoPanel.text($infoPanel.text() + data.data)
      $infoPanel.scrollTop($infoPanel.prop('scrollHeight'))
    }
    // ajax -- post the job:
    $.ajax({
      url: '/plot',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(parameters),
      dataType: 'json',
      success: function (data) {
        console.log('Responded:', data)
        if (data.status == 'success') {
          $(`#${data.jobID} .card-footer`).html('Completed at <code>' + Date() + '</code>.')
          $(`#${data.jobID} .view_individual`).append(data.plot_individual)
          $(`#${data.jobID} .view_combined`).append(data.plot_combined)
          $(`#${data.jobID}_nav`).text('At ' + data.temperature.toString() + 'K')
          serverEventListeners[data.jobID].close()

          // Set the view type to combined after the job is done.
          currentViewType = 'combined'
          $('#button_to_view_combined').click()
          updateAllTabViews()

          console.log($(`#${data.jobID} .view_info`).get())
          Prism.highlightElement($(`#${data.jobID} .view_info`).get()[0])
          $btn.prop('disabled', false).text('Plot')
        } else {
          $(`#${data.jobID}_nav`).text('Failed Job')
          serverEventListeners[data.jobID].close()
          console.log($(`#${data.jobID} .view_info`).get())
          Prism.highlightElement($(`#${data.jobID} .view_info`).get()[0])
          $btn.prop('disabled', false).text('Plot')
        };
      },
      error: function (xhr, ajaxOptions, thrownError) {
        // This should seldomly happen. This is triggered nearly only when the connection fails.
        $btn.prop('disabled', false).text('Plot') // On error do this
      }
    })
  };
}

cheat = function () {
  const reversed_coefficient_dict = dict_reverse(puzzleData.coefficient_dict)
  for (let i in puzzleData.coefficient_array) { // for each pre-set reaction:
    const rxn = puzzleData.coefficient_array[i]
    // console.log(rxn);
    const rxn_slots = ['', '', '', '']
    for (const j in rxn) { // for each cofficient recorded in this particular reaction:
      var if_bad = false
      const this_species = reversed_coefficient_dict[j]
      // console.log(this_species, rxn[j]);
      if (rxn[j] == 1) {
        if (rxn_slots[0] == '') {
          rxn_slots[0] = this_species
        } else if (rxn_slots[1] == '') { // first slot for reactant is occupied.
          rxn_slots[1] = this_species
        } else {
          console.log('Too many reactants given.')
          if_bad = true
          break // prevent even going into the next species/coefficient.
        };
      } else if (rxn[j] == 2) {
        if (rxn_slots[0] == '' && rxn_slots[1] == '') {
          rxn_slots[0] = this_species
          rxn_slots[1] = this_species
        } else {
          console.log('Too many reactants given.')
          if_bad = true
          break // prevent even going into the next species/coefficient.
        };
      } else if (rxn[j] == -1) {
        if (rxn_slots[2] == '') {
          rxn_slots[2] = this_species
        } else if (rxn_slots[3] == '') { // first slot for product is occupied.
          rxn_slots[3] = this_species
        } else {
          console.log('Too many products given:', rxn_slots)
          if_bad = true
          break // prevent even going into the next species/coefficient.
        };
      } else if (rxn[j] == -2) {
        if (rxn_slots[2] == '' && rxn_slots[3] == '') {
          rxn_slots[2] = this_species
          rxn_slots[3] = this_species
        } else {
          console.log('Too many products given.')
          if_bad = true
          break // prevent even going into the next species/coefficient.
        };
      } else if (rxn[j] != 0) {
        console.log('Bad coefficient recorded.')
        if_bad = true
        break // prevent even going into the next species/coefficient.
      };
      // console.log(rxn_slots);
    }
    if (if_bad) {
      console.log('Error happened while parsing a coefficient. Skipping to next pre-recorded reaction.')
      continue // to next reaction
    } else { // now write this reaction to table
      addElementaryReaction()
      const selects = $('td > select', $('#elementaryReactionsTbody > tr').last())
      for (i = 0; i < 4; i++) {
        $(selects[i]).val(rxn_slots[i])
      }
      checkBalance($('#elementaryReactionsTbody > tr').last())
    };
  }
  checkOverallBalance()
}
initializePuzzle = function (data) {
  // Start filling up Selects
  $.each(data.coefficient_dict, function (key, element) {
    emptyElementaryReaction.children('td').children('select').append($('<option>', {
      value: key,
      text: key
    }))
  })
  // Add the first reaction onto the UI:
  addElementaryReaction()
  // fill up the configuration table:
  $.each(data.coefficient_dict, function (key, element) {
    if ($.inArray(key, data.reagents) > -1) { // this species is a reactant
      $('#conditionTbody').prepend(`
                <tr class="reactant" draggable="true">
                    <td class="species" draggable="true">
                        ` + key + `
                    </td>
                    <td>
                        <input class="amount" type="number" value="1" min="0"></input>
                    </td>
                    <td>
                        <input class="temperature" type="number" value="273.15" min="0"></input>
                    </td>
                </tr>`)
    } else { // this species is a product or intermediate
      $('#conditionTbody').append(`
                <tr class="nonReactant" draggable="true">
                    <td class="species" draggable="true">
                        ` + key + `
                    </td>
                    <td>
                        -
                    </td>
                    <td>
                        -
                    </td>
                </tr>`)
    };
  })
  // Start binding drag events:
  $('#conditionTbody>tr>td.species').on('dragstart', function (evt) {
    evt.originalEvent.dataTransfer.setData('species', $(this).text().trim())
  })
}

function applyViewToTab ($pane, viewType) {
  $pane.find('.view_individual, .view_combined, .view_info').hide()
  const view = $pane.find(`.view_${viewType}`)
  console.log('Revealing view:', view)
  view.show()
}

function updateAllTabViews () {
  $('#result_panels .tab-pane').each(function () {
    applyViewToTab($(this), currentViewType)
  })
}

const sortableParams = {
  ghostClass: 'bg-info', // Class name for the drop placeholder
  chosenClass: 'bg-primary', // Class name for the chosen item
  animation: 150 // ms, animation speed moving items when sorting, `0` — without animation
}
$(function () {
  console.log('Play.js loaded.')
  // View Type Radio Handler
  $('input[name="viewType"]').on('change', function () {
    currentViewType = $(this).val()
    console.log('Current view type changed to:', currentViewType)
    updateAllTabViews()
  })
  updateAllTabViews()
  // Select Puzzle to load:
  initializePuzzle(puzzleData)
  // bind events:
  $('#addElementaryReaction').click(addElementaryReaction)
  $('#plotButton').click(plot)
  Sortable.create(document.getElementById('elementaryReactionsTbody'), sortableParams)
  Sortable.create(document.getElementById('conditionTbody'), sortableParams)
  Sortable.create(document.getElementById('result_nav'), sortableParams)
  cheet('c h e a t', cheat)
})
