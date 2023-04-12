function _(a) {
    let ret = document.getElementById(a);
    ret.add = function(x) { ret.appendChild(x); return ret; };
    return ret;
}

function showTab(t) {
	for (let el of document.getElementsByClassName('tabGroupMain')) {
		el.style.display = 'none';
	}
	_('div' + t).style.display = '';
}

function allowancePostprocess(s) {
	if (s.indexOf('NotEnoughAllowance') != -1) {
		return "Your access key ran out of gas allowance. Please log out and log in again to continue."
	}
	return s;
}

function errorOut(e) {
	showTab('Failure');
	_('spanErrorMessage').innerText = '\n\n\nE0 ' + e.toString();
	if (e['message']) {
		try {
			let m = e['message'].replace(/&#39;/g, '"');
			let pos = m.indexOf(', src');
			if (pos != -1) {
				m = m.substr(0, pos);
			}

			_('spanErrorMessage').innerText = allowancePostprocess(m);
		} catch {
			_('spanErrorMessage').innerText = e.toString();
		}
	} else {
		_('spanErrorMessage').innerText = allowancePostprocess(e);
	}
	for (let k in e) {
		console.log(k);
	}
	console.error(typeof e);
	console.error(e);
}

function ff(response) {
	if (!response.ok) {
		response.text().then(text => {
			if (text.startsWith('Traceback')) {
				text = text.trim().split('\n').splice(-1)[0];
			}
			errorOut(Error("Request to server failed with: " + response.statusText + "\n\n" + text))
		})
	}
	return response.text()
}

function formatMicroNear(x) {
	function pad1(x) { if (x % 10 == 0) return pad(x / 10); if (x < 100) return '00' + x; if (x < 10) return '0' + x; return x; }
	function pad(x) { if (x < 10) return '0' + x; return x }
	if (x >= 1000) { return "Ⓝ " + (Math.floor(x / 1000)) + '.' + (x % 1000 == 0 ? "00" : pad1(((x % 1000)))) }
	else {
		return "Ⓝ 0." + pad1(x);
	}
}

function query(page, data, callback) {
	let body = {
		account_id: account_id,
		...data
	};
	console.log(body);
	fetch(page, {'method': 'POST', 'headers': { 'Content-Type': 'application/json' }, 'body': JSON.stringify(body)}).then(response => ff(response).then(x => callback(x))).catch(errorOut);
}

function submitReview( verdict, quality, comment) {
	if (comment.trim().length == 0) {
		alert("Please provide your feedback");
		return;
	}
	if (confirm('Are you sure you want to ' + ['Reject', 'Accept'][verdict] + ' this task?')) {
		query('submit_review', {'verdict': verdict, 'quality': quality, 'comment': comment}, x => {
			if (x == 'ok')
				window.close();
			alert(x)
		});
	}
}

function loadTaskInner(userTaskId, x, reviewTimeLeft) {
	let j = JSON.parse(x);
	showTab('Task');
	let status_str = "It is presently " + [null, "being reviewed", "accepted", "rejected", "abandoned", "postponed"][j['status']] + '.';
	_('divTask').innerHTML = `<b>${j['short_descr']}</b> :: <a href=# onclick="showTasksets()">Back to task selection</a><br>Reward: <b>${formatMicroNear(j['reward'])}</b>. Please review the task below. Time left: <b>${reviewTimeLeft}</b><br><br>`

	if (j['comment']) {
		_('divTask').appendChild(_c('span')).innerHTML = 'This work has been resubmitted. The author left the following comment: ';
		let commentSpan = _('divTask').appendChild(_c('span'));
		commentSpan.innerText = j['comment'];
		commentSpan.style.color = 'darkgreen';
		_('divTask').appendChild(_c('hr'));
	}

	let reviewCommentArea = _('divTask').appendChild(_c('textarea'));
	reviewCommentArea.rows = 5;
	reviewCommentArea.cols = 50;
	reviewCommentArea.placeholder = 'Provide review feedback (even if you accept the task)';
	_('divTask').appendChild(_c('br'));
	let verdicts = [0, 0, 1, 1, 1]
	let qualities = [4, 0, 0, 1, 2]
	let texts = ['Report', 'Reject / Has Mistakes', 'Low Quality', 'Good Quality', 'Outstanding']
	let clrs = ['#000000', '#FFD0DD', '#F0FFF0', '#F0FFF0', '#F0FFF0', '#F0FFF0'];
	for (let i = 0; i < 5; i += 1) {
		let btn = _('divTask').appendChild(document.createElement('button'));
		if (i == 0) btn.style.color = 'red';
		btn.style.backgroundColor = clrs[i];
		btn.innerText = texts[i];
		btn.style.marginRight = '20px';

		btn.onclick = () => { submitReview(verdicts[i], qualities[i], reviewCommentArea.value.trim()) };
	}

	_('divTask').appendChild(_c('br'));
	_('divTask').appendChild(_c('br'));

	if (j['reviews'].length > 0)
		_('divTask').appendChild(_c('u')).innerText = 'Previous reviews:\n';
	
	if (j['reviews'].length > 0) {
		let atLeastOneOld = false;
		let nextReviewerOrd = 1;

		for (let i = 0; i < j['reviews'].length; ++ i) {
			let review = j['reviews'][i];
			if (review.before_resubmit) {
				atLeastOneOld = true;
			}
		}

		if (atLeastOneOld) {
			_('divTask').appendChild(_c('div')).innerHTML = '<br>Reviews printed <font color=gray>in gray</font> are for a previous version of the task. The author has resubmitted the task. The author has either fixed the issues, or doesn\'t agree with them.<br><br>';
		}

		for (let i = 0; i < j['reviews'].length; ++ i) {
			let review = j['reviews'][i];
			let who = '';
			if (review.mine) {
				who = '<font color=darkgreen>Me</font>'
			} else if (review.reported) {
				who = '<font color=darkred>REPORTED</font>'
			} else {
				who = 'Reviewer #' + nextReviewerOrd;
				nextReviewerOrd += 1;
			}

			_('divTask').appendChild(_c('b')).innerHTML = who + ': ';
			let reviewContentSpan = _('divTask').appendChild(_c('span'));

			if (review.before_resubmit) {
				reviewContentSpan.style.color = 'gray';
			}

			let qualityS = '';
			if (review.reported) {
				reviewContentSpan.style.color = 'darkred';
				if (review.before_resubmit) {
					reviewContentSpan.style.color = '#FF8080';
				}
				if (review['verdict'] != 0) {
					qualityS = '[' + ['Low', 'Good', 'Outstanding', '', 'HM'][review['quality']] + ']'
				}
			}
			reviewContentSpan.innerText = qualityS + '[' + ({'-1': 'In Review', 0: 'Rejected', 1: 'Accepted'})[review['verdict']] + '] ' + review['comment'] + " ";
			let reportSup = _('divTask').appendChild(_c('sup'));
			let reportA = reportSup.appendChild(_c('a'));
			let reportOrd = i;
			if (j['mode'] == 'task' || j['mode'] == 'otask') {
				reportOrd = 'last';
			}
			reportA.innerText = '[report]';
			reportA.href = '#';
			reportA.onclick = () => {
				let a = prompt('Provide a short description of the issue:');
				if (a) {
					reportSup.innerHTML = '<i>reporting...</i>'
					query('report_review', {task_id: userTaskId, reportOrd: reportOrd, reason: encodeURIComponent(a)}, () => reportSup.innerHTML = '<b>reported</b>');
				}
			}
			_('divTask').appendChild(_c('br'));
		}

		_('divTask').appendChild(_c('br'));
		_('divTask').appendChild(_c('hr'));
	}


	_('divTask').appendChild(_c('span')).innerText = j['long_descr'];

	_('divTask').appendChild(_c('br'));
	_('divTask').appendChild(_c('br'));

	let pillarEditor = null;

	_('divTask').appendChild(_c('hr'));
	let holder = _('divTask').appendChild(_c('span'));
	let pillar_id = j['pillar_id'];
	holder.innerHTML = "<i>Loading...</i>"

	if (j['nightsky_exercises'][0]) {
		let exercises_holder = _('divTask').appendChild(_c('span'));

		exercises_holder.innerHTML = '<br><hr><br><b>Sample Puzzles:</b><br>Solve the following 5 sample puzzles. Note the following:<br>1. Only choose "Exercise is incorrect" if there\'s no way to solve the puzzle. If you *can* solve the puzzle, but the puzzle has some other issues (e.g. the format of the answer is unclear, or there are issues with spelling), solve the puzzle, do not click on "Exercise is incorrect", and point out such mistakes in the overall task verdict.<br>2. The author of the submission will not see the sample puzzles when they receive your verdict. If there are some issues with some of the puzzles, provide enough information in your comments for the author to understand what particular instantiation of his script have issues.<br><br>';

		for (let i = 0; i < 5; ++ i) {
			let innerId = i;
			exercises_holder.appendChild(_c('u')).innerText = '\nSample #' + (i + 1) + "\n";
			exercises_holder.appendChild(_c('b')).innerText = 'Task: ';
			exercises_holder.appendChild(_c('span')).innerText = j['nightsky_exercises'][i]['descr'] + '\n';

			let table = exercises_holder.appendChild(_c('table'));
			let tbody = table.appendChild(_c('tbody'));
			let headerTr = tbody.appendChild(_c('tr'));
			headerTr.appendChild(_c('td')).innerHTML = '<b>Input</b>';
			headerTr.appendChild(_c('td')).innerHTML = '&nbsp;&nbsp;&nbsp;';
			headerTr.appendChild(_c('td')).innerHTML = '<b>Output</b>';
			let dataTr = tbody.appendChild(_c('tr'));
			let inputTd = dataTr.appendChild(_c('td'));
			dataTr.appendChild(_c('td'));
			let outputTd = dataTr.appendChild(_c('td'));
			inputTd.vAlign = 'top';
			outputTd.vAlign = 'top';
			outputTd.appendChild(_c('u')).innerText = '\nSolution 1:\n';
			let correctHolder = outputTd.appendChild(_c('div'));
			outputTd.appendChild(_c('u')).innerText = '\nSolution 2:\n';
			let incorrectHolder = outputTd.appendChild(_c('div'));
			let imagesHolder = {}
			renderValue(j['nightsky_exercises'][i]['input'], inputTd, imagesHolder);
			renderValue(j['nightsky_exercises'][i]['output'], correctHolder, imagesHolder);
			renderValue(j['nightsky_exercises'][i]['wrong_output'], incorrectHolder, imagesHolder);

			let reviewHolder = exercises_holder.appendChild(_c('div'));
			function redrawWithStatus(s, a, c) {
				reviewHolder.innerHTML = '';
				reviewHolder.appendChild(_c('span')).innerText = "\nYour answer: ";
				let btns = [reviewHolder.appendChild(document.createElement('button')), reviewHolder.appendChild(document.createElement('button')), reviewHolder.appendChild(document.createElement('button'))]
				for (let i = 0; i < 3; i += 1) {
					btns[i].style.marginLeft = '10px'
					if (i < 2) {
						btns[i].innerText = 'Approve Solution ' + (i + 1);
					} else {
						btns[i].innerText = 'Exercise is incorrect';
					}

					if (i < 2 && s != 2) {
						btns[i].onclick = function() {
							btns[i].innerText = 'Approving ...'
							btns[0].disabled = true;
							btns[1].disabled = true;
							btns[2].disabled = true;
							query('answer_exercise', {pillar_id: j['pillar_id'], innerId: innerId, answer: i}, resp => {
								let j = JSON.parse(resp);
								redrawWithStatus(j['status'], j['answer'], j['comment']);
							});
						}
					} else if (i == 2) {
						btns[i].onclick = function() {
							let comment = prompt("Provide detailed feedback on why the exercise is incorrect:")
							if (comment && comment.trim()) {
								btns[i].innerText = 'Sending feedback...'
								btns[0].disabled = true;
								btns[1].disabled = true;
								btns[2].disabled = true;
								query('answer_exercise', {pillar_id: j['pillar_id'], innerId: innerId, answer: 4, comment: comment}, resp => {
									let j = JSON.parse(resp);
									redrawWithStatus(j['status'], j['answer'], j['comment']);
								});
							}
						}
					}
				}
				btns[1].style.marginRight = '10px'
				btns[2].style.marginRight = '10px'
				if (a !== undefined) {
					if (s == 2) {
						btns[a].style.backgroundColor = '#E0FFE0'
					} else if (s == 1) {
						btns[a].style.backgroundColor = '#E0FFE0'
						reviewHolder.appendChild(_c('span')).innerText = 'You initially answered wrong.';
					} else if (s == 3) {
						btns[1 - a].style.backgroundColor = '#FFE0E0'
						reviewHolder.appendChild(_c('span')).innerText = '\nYour answer doesn\'t match the answer of the author. Review the puzzle carefully, and do one of the two actions:\n1. If you indeed answered wrong, click on the correct answer. You will get a penalty (irregardless of whether the task itself will be approved or rejected). If you accumulate five penalties, you will not be able to conduct reviews for one months.\n2. Otherwise, if the answer you gave is correct, or if the puzzle is generally done incorreclty, click "Exercise is incorrect", provide the feedback, and then reject the entire submission. There\'s zero tolerance for mistakes in puzzles.';
					} else if (s == 4) {
						btns[2].style.backgroundColor = '#FFE0E0'
						let sp = reviewHolder.appendChild(_c('span'));
						sp.innerText = "\nYour comment: " + c;
						sp.style.color = 'darkred';
					}
				}
			}

			if (j['mode'] == 'review' || j['mode'] == 'oreview') {
				if (!j['nightsky_answers'][innerId]) {
					redrawWithStatus(0, 0, '')
				} else {
					console.log(j['nightsky_answers'][innerId]['status'], j['nightsky_answers'][innerId]['answer'], j['nightsky_answers'][innerId]['comment'])
					redrawWithStatus(j['nightsky_answers'][innerId]['status'], j['nightsky_answers'][innerId]['answer'], j['nightsky_answers'][innerId]['comment'])
				}
			}
		}
	}

	function showPillar(s) {
		let pillar = JSON.parse(s);
		pillarEditor = createPillarEditor(pillar, holder, null, true, true);
	}

	query('/pillar', {pillar_id: pillar_id}, showPillar);
	_('divTask').appendChild(_c('span')).innerText = '\n\n\n\n\n';
}

function loadReview(userTaskId, reviewTimeLeft) {
	console.log(userTaskId)
	query('/get_task', {task_id: userTaskId}, x => loadTaskInner(userTaskId, x, reviewTimeLeft));
}

params = new URLSearchParams(window.location.search);
var account_id = params.get('account_id');
var mode = 37;
query('/status', {}, x => {
	j = JSON.parse(x);
	loadReview(j['user_task_id'], j['time_left']);
});