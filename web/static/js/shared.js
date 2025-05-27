/* global $ */
// shared.js: Utility functions and helpers for both create.js and play.js

/**
 * Reverse dictionary mapping {key: value} -> {value: key}
 * @param {Object} obj
 * @returns {Object}
 */
export function reverseDict (obj) {
  const reversed = {}
  for (const key in obj) {
    if (Object.hasOwn(obj, key)) {
      reversed[obj[key]] = key
    }
  }
  return reversed
}

/**
 * Parse a chemical formula into atom counts.
 * @param {string} species
 * @param {Object} atomsArray
 * @param {boolean} ifReactant
 * @returns {Object}
 */
export function moleculeToAtoms (species, atomsArray, ifReactant) {
  const atoms = species.match(/([A-Z][a-z]?)(\d*)/g) || []
  for (const atom of atoms) {
    const number = parseInt(atom.replace(/[^\d]/g, ''), 10) || 1
    const element = atom.replace(/\d*/g, '')
    if (ifReactant) {
      atomsArray[element] = (atomsArray[element] || 0) + number
    } else {
      atomsArray[element] = (atomsArray[element] || 0) - number
    }
  }
  return atomsArray
}

/**
 * Check if a reaction row is balanced and update its style.
 * @param {jQuery} row
 * @param {string} inputSelector - 'input' for create.js, 'select' for play.js
 * @returns {boolean}
 */
export function checkBalance (row, inputSelector = 'input') {
  const cells = $(`td>${inputSelector}`, row).toArray()
  let atomsArray = {}
  for (let i = 0; i < cells.length; i++) {
    const species = cells[i].value
    if (species === '') continue
    atomsArray = moleculeToAtoms(species, atomsArray, i < 2)
  }
  if (
    Object.keys(atomsArray).length === 0 ||
    (cells[0].value === cells[2].value && cells[1].value === cells[3].value) ||
    (cells[0].value === cells[3].value && cells[1].value === cells[2].value)
  ) {
    row.removeClass('bg-danger-subtle bg-success-subtle')
    return false
  } else {
    let ifBalanced = true
    for (const i in atomsArray) {
      if (atomsArray[i] !== 0) {
        ifBalanced = false
        break
      }
    }
    if (ifBalanced) {
      row.removeClass('bg-danger-subtle').addClass('bg-success-subtle')
    } else {
      row.addClass('bg-danger-subtle').removeClass('bg-success-subtle')
    }
    return ifBalanced
  }
}

/**
 * Check if all reactions are valid and enable/disable the proceed/plot button.
 * @param {string} rowSelector
 * @param {string} buttonSelector
 */
export function checkOverallBalance (rowSelector, buttonSelector) {
  if (
    $(`${rowSelector}.bg-danger-subtle`).length === 0 &&
    $(`${rowSelector}.bg-success-subtle`).length > 0
  ) {
    $(buttonSelector).removeClass('disabled').prop('disabled', false)
  } else {
    $(buttonSelector).addClass('disabled').prop('disabled', true)
  }
}
