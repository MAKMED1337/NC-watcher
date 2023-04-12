const sleep = ms => new Promise(r => setTimeout(r, ms));
var review_cycle = -1;
var last_status = {};

function claim_review(element) {
	if (review_cycle == -1) {
		review_cycle = setTimeout(claim_review_routine, 0);
		element.textContent = 'stop reviewing';
		return;
	}

	console.log('clear', review_cycle);
	clearTimeout(review_cycle);
	review_cycle = -1;
	element.textContent = 'start reviewing';
}

function notify(account_id) {
	Notification.requestPermission().then(async (perm) => {
		if (perm !== 'granted') {
			alert('allow notifications');
			return;
		}
	
		new Notification('review found ', {body: account_id})
	})
}

async function claim_review_routine() {
	resp = await fetch('/claim_review');
	j = await resp.json();

	table = document.getElementById('status');
	while (table.rows.length > 1)
		table.deleteRow(-1);
	
	for (let key of Object.keys(j).sort()) {
		let value = j[key];
		s = value['status'];
		row = table.insertRow(-1);
		row.insertCell(-1).textContent = key;
		row.insertCell(-1).textContent = s;

		if (s != last_status[key] && s == 'has_review')
			notify(key);
		last_status[key] = s;
	}

	if (review_cycle != -1)
		review_cycle = setTimeout(claim_review_routine, 10000);
}