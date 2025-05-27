/* global $, _, Sortable, cheet, bootstrap */
/**
 * CKWatson Puzzle Creation Page JS
 * Handles dynamic UI and logic for creating new chemical kinetics puzzles.
 * Modernized for ES6+ and maintainability.
 */

import {
  moleculeToAtoms,
  checkBalance,
  checkOverallBalance
} from './shared.js'

// Utility functions
$.urlParam = function (name) {
  const results = new RegExp('[?&]' + name + '=([^&#]*)').exec(
    window.location.href
  )
  if (!results) return ''
  return results[1] || ''
}
const emptyElementaryReaction = $(
  `<tr class="elementaryReaction" draggable="true">
      <td class="bg-transparent"><input class="form-control"></input></td>
      <td class="bg-transparent">+</td>
      <td class="bg-transparent"><input class="form-control"></input></td>
      <td class="bg-transparent">=</td>
      <td class="bg-transparent"><input class="form-control"></input></td>
      <td class="bg-transparent">+</td>
      <td class="bg-transparent"><input class="form-control"></input></td>
      <td class="bg-transparent">
        <button class="btn btn-danger btn-sm removeReaction">Remove</button>
        <button class="btn btn-success btn-sm balanceReaction">Balance</button>
      </td>
  </tr>`
)

/**
 * Add a new row for an elementary reaction.
 */
const checkAndUpdateProceedButton = () => {
  checkOverallBalance('#proceedButton')
}

const addElementaryReaction = () => {
  const thisElementaryReaction = emptyElementaryReaction.clone()
  $('#elementaryReactionsTbody').append(thisElementaryReaction)
  const cells = thisElementaryReaction.children('td')
  cells.children('button.removeReaction').click(removeElementaryReaction)
  cells.children('button.balanceReaction').click(balanceElementaryReaction)
  cells.children('input').on('change', onSelectChange)
  checkAndUpdateProceedButton()
}

/**
 * Remove an elementary reaction row.
 */
const removeElementaryReaction = function () {
  const thisRow = $(this).closest('tr')
  thisRow.remove()
  checkAndUpdateProceedButton()
}

/**
 * Attempt to balance an elementary reaction row.
 */
const balanceElementaryReaction = function () {
  const thisRow = $(this).closest('tr')
  const speciesList = $('input', thisRow).map((i, obj) => $(obj).val())
  let atomsArray = {}
  for (let i = 0; i < 3; i++) {
    const species = speciesList[i]
    if (species === '') continue
    atomsArray = moleculeToAtoms(species, atomsArray, i < 2)
  }
  let guessedSpecies = ''
  for (const i in atomsArray) {
    const number = atomsArray[i]
    if (number > 0) {
      guessedSpecies += i
      if (number > 1) guessedSpecies += number
    }
  }
  $('td:nth-child(7) > input', thisRow).val(guessedSpecies)
  checkBalance(thisRow, 'input')
  checkAndUpdateProceedButton()
}

/**
 * On change of any input in a reaction row, re-check balance.
 */
const onSelectChange = function () {
  const thisRow = $(this).closest('tr')
  checkBalance(thisRow, 'input')
  checkAndUpdateProceedButton()
}

/**
 * Fill in test reactions for quick demo/testing.
 */
const cheat = () => {
  const testRxns = [
    ['NO', 'NO', 'N2O2', ''],
    ['N2O2', 'Br2', 'NOBr', 'NOBr']
  ]
  for (const rxn of testRxns) {
    addElementaryReaction()
    const selects = $('td > input', $('#elementaryReactionsTbody > tr').last())
    for (let i = 0; i < 4; i++) {
      $(selects[i]).val(rxn[i])
    }
    checkBalance($('#elementaryReactionsTbody > tr').last(), 'input')
  }
  checkAndUpdateProceedButton()
}

$(function () {
  // Bind events
  $('#addElementaryReaction').click(addElementaryReaction)
  $('#proceedButton').click(function () {
    proceed()
    $('#speciesModal').modal('show')
  })
  $('#saveButton').click(save)
  // Enable plugins
  Sortable.create(
    document.getElementById('elementaryReactionsTbody'),
    sortableParams
  )
  cheet('c h e a t', cheat)
  // Create the first elementary reaction row
  addElementaryReaction()
})

/**
 * Add a row for a species in the modal.
 * @param {string} speciesName
 */
const addSpeciesRow = (speciesName) => {
  if (!speciesName) {
    console.log('Empty speciesName given. Skipped.')
    return
  }
  const $this = $(
    `<tr draggable="true">
      <td class="speciesName">${speciesName}</td>
      <td class="energy"><input type="number" value="${_.random(0, 500)}"></td>
      <td class="input-group">
        <span class="input-group-addon">
          <input class="ifReactant" type="checkbox" checked>
        </span>
        <span class="input-group-btn">
          <button type="button" class="btn btn-default btn-sm editPERsButton dropdown-toggle" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false" title="Select which reactions this species is a reagent for. (Checked = this species is a reagent in that reaction)" data-bs-toggle="tooltip" data-bs-placement="top">
            <span class="bi bi-gear"></span> <span class="bi bi-caret-down-fill"></span>
          </button>
          <ul class="PERs dropdown-menu p-2" style="min-width: 340px;">
            <li class="dropdown-header fw-bold text-primary pb-2">During ${speciesName}'s pre-equilibrium process, these reactions should happen:</li>
          </ul>
        </span>
      </td>
    </tr>`
  )
  const options = []
  $('.dropdown-menu a', $this).on('click', function (event) {
    const $target = $(event.currentTarget)
    const val = $target.attr('data-value')
    const $inp = $target.find('input')
    let idx
    if ((idx = options.indexOf(val)) > -1) {
      options.splice(idx, 1)
      setTimeout(() => $inp.prop('checked', false), 0)
    } else {
      options.push(val)
      setTimeout(() => $inp.prop('checked', true), 0)
    }
    $(event.target).blur()
    return false
  })
  for (const i in reactions) {
    const reactionDescription = `${reactions[i][0]} + ${reactions[i][1]} → ${reactions[i][2]} + ${reactions[i][3]}`
    let thisCheckbox
    if ($.inArray(speciesName, reactions[i]) > -1) {
      thisCheckbox = $(
        `<li class="dropdown-item px-2 py-1 d-flex align-items-center">
          <input type="checkbox" checked class="form-check-input me-2 rxn${i}" style="margin-top:0;" title="This species is a reagent in this reaction.">
          <span>${reactionDescription}</span>
        </li>`
      )
    } else {
      thisCheckbox = $(
        `<li class="dropdown-item px-2 py-1 d-flex align-items-center">
          <input type="checkbox" disabled class="form-check-input me-2 rxn${i}" style="margin-top:0;" title="This species does not participate in this reaction.">
          <span class="text-muted">${reactionDescription}</span>
        </li>`
      )
    }
    $('.dropdown-menu', $this).append(thisCheckbox)
  }
  $('#speciesTbody').append($this)
  $('.ifReactant', $this).click(function () {
    const $row = $(this).closest('tr')
    $('.editPERsButton', $row).toggleClass('disabled')
    $('#saveButton').prop(
      'disabled',
      $('#speciesTbody .ifReactant:checked').length === 0
    )
  })
  // Enable Bootstrap tooltips for dynamically created elements
  setTimeout(() => {
    $("[data-bs-toggle='tooltip']", $this).tooltip({ trigger: 'hover' })
  }, 0)
}

let reactions
let speciesList

/**
 * Gather reactions and species, populate modal, and suggest puzzle name.
 */
const proceed = () => {
  speciesList = []
  reactions = $.makeArray(
    $('#elementaryReactionsTbody>tr.bg-success-subtle').map(function () {
      return [
        $('td>input', this)
          .map(function () {
            speciesList.push(this.value)
            return this.value
          })
          .toArray()
      ]
    })
  ).sort()
  $('#speciesTbody').html('')
  speciesList = _.uniq(speciesList, (item) => item)
  _.each(speciesList, addSpeciesRow)
  if ($('#puzzleName').val() === 'Untitled Puzzle') {
    $('#puzzleName').val(speciesList.join(' '))
  }
}

/**
 * Show a Bootstrap Toast alert at the top right of the page.
 * @param {string} status - Bootstrap alert status (success, danger, warning, info)
 * @param {string} message - Message to display
 */
const pushAlert = (status, message) => {
  // Remove any previous toast
  $('#ckwatson-toast').remove()
  // Toast HTML
  const toastHtml = `
    <div id="ckwatson-toast" class="toast align-items-center text-bg-${status} border-0 position-fixed top-0 end-0 m-3" role="alert" aria-live="assertive" aria-atomic="true" style="z-index: 9999; min-width: 300px;">
      <div class="d-flex">
        <div class="toast-body">
          ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>`
  // Append to body
  $('body').append(toastHtml)
  // Show toast using Bootstrap 5
  const toastEl = document.getElementById('ckwatson-toast')
  const toast = new bootstrap.Toast(toastEl, { delay: 3000 })
  toast.show()
}

// Utility: Validate puzzle name for safe filename (alphanumeric, dash, underscore, space)
function isValidPuzzleName (name) {
  return /^[\w\- ]+$/.test(name)
}

/**
 * Save the puzzle by sending data to the backend.
 */
const save = function () {
  const $btn = $(this).button('loading')
  const puzzleName = $('#puzzleName').val()
  if (!isValidPuzzleName(puzzleName)) {
    pushAlert(
      'danger',
      'Invalid puzzle name. Use only letters, numbers, spaces, dashes, and underscores.'
    )
    $btn.button('reset')
    return
  }
  const speciesNames = []
  const speciesIfReactants = []
  const speciesEnergies = []
  const reagentPERs = {}
  $('#speciesTbody > tr').each(function () {
    const $this = $(this)
    const name = $('.speciesName', $this).text().trim()
    const ifReactant = $('.ifReactant', $this).is(':checked')
    if (ifReactant) {
      const reagentPER = $('.PERs input', $this)
        .map(function () {
          return this.checked
        })
        .get()
      reagentPERs[name] = reagentPER
    }
    const energy = parseFloat($('.energy > input', $this).val())
    speciesNames.push(name)
    speciesIfReactants.push(ifReactant)
    speciesEnergies.push(energy)
  })
  const parameters = {
    auth_code: $('#auth_code').val(),
    puzzleName: $('#puzzleName').val(),
    reactions,
    speciesNames,
    speciesIfReactants,
    speciesEnergies,
    reagentPERs
  }
  console.log('About to send data to server:', parameters)
  $.ajax({
    url: '/save',
    type: 'POST',
    contentType: 'application/json',
    data: JSON.stringify(parameters),
    dataType: 'json',
    success: function (data) {
      console.log('Server responded:', data)
      pushAlert(data.status, data.message)
      $btn.button('reset')
      if (data.status === 'success') {
        // Show the success message, then reset the form for a new puzzle
        $('#speciesModal').modal('hide')
        $('#elementaryReactionsTbody').empty()
        addElementaryReaction()
        $('#speciesTbody').empty()
        $('#puzzleName').val('Untitled Puzzle')
        $('#auth_code').val('')
        $('#proceedButton').addClass('disabled').prop('disabled', true)
      }
    },
    error: function (xhr, ajaxOptions, thrownError) {
      pushAlert('danger', 'Error contacting the server: ' + thrownError)
      $btn.button('reset')
    }
  })
}

// Utility and UI helpers
const sortableParams = {
  ghostClass: 'bg-info',
  chosenClass: 'bg-primary',
  animation: 150
}
