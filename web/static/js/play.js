import { reverseDict, checkBalance, checkOverallBalance } from './shared.js'
/* global $, md5, puzzleName, puzzleData, ip, Sortable, Prism, cheet, EventSource */

let currentViewType = 'info'

const emptyElementaryReaction = $(`
  <tr class="elementaryReaction" draggable="true">
    <td class="bg-transparent"><input type="checkbox" class="form-check-input" checked></td>
    <td class="bg-transparent"><select class="form-control"><option value=""></option></select></td>
    <td class="bg-transparent">+</td>
    <td class="bg-transparent"><select class="form-control"><option value=""></option></select></td>
    <td class="bg-transparent">=</td>
    <td class="bg-transparent"><select class="form-control"><option value=""></option></select></td>
    <td class="bg-transparent">+</td>
    <td class="bg-transparent"><select class="form-control"><option value=""></option></select></td>
    <td class="bg-transparent"><button type="submit" class="btn btn-danger btn-sm removeReaction">Remove</button></td>
  </tr>
`)

/** Handler for select change in a reaction row */
const onSelectChange = function () {
  const row = $(this).closest('tr')
  checkBalance(row, 'select')
  checkOverallBalance('#plotButton')
}

/** Remove a reaction row */
const removeElementaryReaction = function () {
  $(this).closest('tr').remove()
  checkOverallBalance('#plotButton')
}

/** Add new reaction row to the DOM and bind behavior */
const addElementaryReaction = () => {
  const newRow = emptyElementaryReaction.clone()
  $('#elementaryReactionsTbody').append(newRow)

  newRow.find('button.removeReaction').click(removeElementaryReaction)
  newRow.find('select').change(onSelectChange)
  newRow
    .find('td>select')
    .on('dragover', (e) => e.originalEvent.preventDefault())
  newRow.find('td>select').on('drop', function (e) {
    const data = e.originalEvent.dataTransfer.getData('species')
    if (data) {
      $(this).val(data).change()
    }
    e.originalEvent.preventDefault()
  })
}
const serverEventListeners = {}
/** Submit reactions to server and initialize job tracking */
const plot = function () {
  // Only include checked reactions that are balanced
  const reactions = Array.from(
    $('#elementaryReactionsTbody>tr.bg-success-subtle')
  )
    .filter((row) => $(row).find('input[type="checkbox"]').prop('checked'))
    .map((row) => {
      return Array.from($(row).find('td > select')).map(
        (select) => select.value
      )
    })

  const temperature = parseFloat($('#reactionTemperature').val(), 10)

  const conditions = $.makeArray(
    $('#conditionTbody > tr.reactant').map(function () {
      return {
        name: $('td.species', this).text().trim(),
        amount: parseFloat($('td>input.amount', this).val()),
        temperature: parseFloat($('td>input.temperature', this).val())
      }
    })
  ).sort()

  const solutionID = md5(JSON.stringify(reactions))
  const conditionID = md5(JSON.stringify(conditions))
  const jobID = `${ip}_${conditionID}_${temperature}_${solutionID}_${Date.now()}`

  if ($(`#${jobID}`).length > 0) {
    $(`#${jobID}_nav`).tab('show')
    return
  }

  const $btn = $(this)
  $btn.prop('disabled', true).text('Loading...')

  const parameters = {
    puzzle: puzzleName,
    reactions,
    temperature,
    conditions,
    jobID,
    solutionID,
    conditionID
  }

  $('#result_panels').append(`
    <div class="tab-pane" id="${jobID}" role="tabpanel">
      <div class="view_individual" style="display:none"></div>
      <div class="view_combined" style="display:none"></div>
      <pre class="view_info language-python"></pre>
      <div class="card-footer"></div>
    </div>
  `)

  $('#result_nav').append(`
    <li class="nav-item" role="presentation">
      <button class="nav-link" id="${jobID}_nav" data-bs-toggle="tab" data-bs-target="#${jobID}" type="button" role="tab">Plotting...</button>
    </li>
  `)

  $(`#${jobID}_nav`).tab('show')
  currentViewType = 'info'
  $('#button_to_view_info').click()

  const source = new EventSource(`/stream?channel=${jobID}`)
  serverEventListeners[jobID] = source

  source.onmessage = (event) => {
    const data = JSON.parse(event.data)
    const $infoPanel = $(`#${jobID} .view_info`)
    $infoPanel.text($infoPanel.text() + data.data)
    $infoPanel.scrollTop($infoPanel.prop('scrollHeight'))
  }

  $.ajax({
    url: '/plot',
    type: 'POST',
    contentType: 'application/json',
    data: JSON.stringify(parameters),
    dataType: 'json',
    success: (data) => {
      console.log(data)
      const job = $(`#${data.jobID}`)
      job.find('.card-footer').html(`Completed at <code>${Date()}</code>`)
      job.find('.view_individual').append(data.plot_individual)
      job.find('.view_combined').append(data.plot_combined)
      const scoreText =
        typeof data.score === 'number'
          ? `Score: ${data.score.toFixed(1)}%`
          : 'No Score'
      $(`#${data.jobID}_nav`).text(scoreText)
      serverEventListeners[data.jobID].close()
      currentViewType = 'combined'
      $('#button_to_view_combined').click()
      updateAllTabViews()
      Prism.highlightElement(job.find('.view_info').get(0))
      $btn.prop('disabled', false).text('Plot')
    },
    error: () => {
      $btn.prop('disabled', false).text('Plot')
    }
  })
}

/** Populate pre-configured reactions into table */
const cheat = () => {
  const reversedDict = reverseDict(puzzleData.coefficient_dict)
  for (const rxn of puzzleData.coefficient_array) {
    const slots = ['', '', '', '']
    let error = false

    for (const [key, coef] of Object.entries(rxn)) {
      const species = reversedDict[key]
      if (!species) continue

      if (coef === 1 || coef === 2) {
        if (slots[0] === '') {
          slots[0] = species
          if (coef === 2) slots[1] = species
        } else if (slots[1] === '') {
          slots[1] = species
        } else {
          console.warn('Too many reactants')
          error = true
          break
        }
      } else if (coef === -1 || coef === -2) {
        if (slots[2] === '') {
          slots[2] = species
          if (coef === -2) slots[3] = species
        } else if (slots[3] === '') {
          slots[3] = species
        } else {
          console.warn('Too many products')
          error = true
          break
        }
      }
    }

    if (!error) {
      addElementaryReaction()
      const selects = $(
        'td > select',
        $('#elementaryReactionsTbody > tr').last()
      )
      for (let i = 0; i < 4; i++) {
        $(selects[i]).val(slots[i])
      }
      checkBalance($('#elementaryReactionsTbody > tr').last(), 'select')
    }
  }
  checkOverallBalance('#plotButton')
}

/** Initialize puzzle UI */
const initializePuzzle = (data) => {
  Object.keys(data.coefficient_dict).forEach((key) => {
    emptyElementaryReaction
      .find('select')
      .append(`<option value="${key}">${key}</option>`)
  })

  addElementaryReaction()

  Object.entries(data.coefficient_dict).forEach(([key]) => {
    const isReactant = data.reagents.includes(key)
    const row = isReactant
      ? `<tr class="reactant" draggable="true"><td class="species" draggable="true">${key}</td><td><input class="amount w-50" type="number" value="1" min="0"></td><td><input class="temperature w-50" type="number" value="273.15" min="0"></td></tr>`
      : `<tr class="nonReactant" draggable="true"><td class="species" draggable="true">${key}</td><td></td><td></td></tr>`
    $('#conditionTbody').append(row)
  })

  $('#conditionTbody>tr>td.species').on('dragstart', function (evt) {
    evt.originalEvent.dataTransfer.setData('species', $(this).text().trim())
  })
}

/** Tab view update utility */
const applyViewToTab = ($pane, viewType) => {
  $pane.find('.view_individual, .view_combined, .view_info').hide()
  $pane.find(`.view_${viewType}`).show()
}

const updateAllTabViews = () => {
  $('#result_panels .tab-pane').each(function () {
    applyViewToTab($(this), currentViewType)
  })
}

// DOM Ready
$(() => {
  console.log('play.js initialized.')
  $('input[name="viewType"]').change(function () {
    currentViewType = $(this).val()
    updateAllTabViews()
  })
  updateAllTabViews()
  initializePuzzle(puzzleData)
  $('#addElementaryReaction').click(addElementaryReaction)
  $('#plotButton').click(plot)

  Sortable.create(
    document.getElementById('elementaryReactionsTbody'),
    sortableParams
  )
  Sortable.create(document.getElementById('conditionTbody'), sortableParams)
  Sortable.create(document.getElementById('result_nav'), sortableParams)

  cheet('c h e a t', cheat)
})

const sortableParams = {
  ghostClass: 'bg-info',
  chosenClass: 'bg-primary',
  animation: 150
}
