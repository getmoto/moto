window.addEventListener('DOMContentLoaded', function () {
  refreshTable();

  const fold = document.getElementById('btn-fold');
  const unfold = document.getElementById('btn-unfold');



  unfold.addEventListener('click', function () {
    collapseElementList = document.querySelectorAll('.collapsed-content')
    collapseElementList.forEach(collapseEl => {
      el = bootstrap.Collapse.getOrCreateInstance(collapseEl, { toggle: false });
      if (el) {
        el.show();
      }
    });
  });

  fold.addEventListener('click', function () {
    collapseElementList = document.querySelectorAll('.collapsed-content')
    collapseElementList.forEach(collapseEl => {
      el = bootstrap.Collapse.getOrCreateInstance(collapseEl, { toggle: false });
      if (el) {
        el.hide();
      }
    });
  });
});

const refreshData = async () => {
  await fetch('moto-api/data.json')
    .then(result => result.json())
    .then(data => {
      updateTable(data);
    });
};

const refreshTable = () => {
  refreshData();
};


/* Data sample
{
  // Service name
  "cloudwatch": {
    // Resource name
    "Alarm": [], //Ressource content (array of objects)
    "Dashboard": [],
    "InsightRule": [],
    "MetricAggregatedDatum": [],
    "MetricDatum": [],
    "MetricDatumBase": []
  },
  "core": {
    "CloudFormationModel": []
  },
  "events": {
    "Archive": [],
    "Connection": [],
    "Destination": [],
    "EventBus": [],
    "PartnerEventSource": [],
    "Replay": [],
    "Rule": []
  }
} 
*/

// Update the div id=data with one table per service
function updateTable(data) {
  const dataContainer = document.getElementById('data');
  if (!dataContainer) {
    console.error('Element with id="data" not found');
    return;
  }

  // Clear existing content
  dataContainer.innerHTML = '';

  // Iterate through each service
  // Each service is a div
  // inside this div, each resource is a table if the resource array is not empty

  Object.keys(data).forEach(serviceName => {
    const resources = data[serviceName];
    //create table object
    const tableDiv = document.createElement('div');
    tableDiv.setAttribute('id', `div-table-${serviceName}`);

    const hr = document.createElement('hr');
    hr.className = 'border border-primary border-2 opacity-75';
    tableDiv.appendChild(hr);

    const serviceTitle = document.createElement('h3');
    serviceTitle.textContent = `${serviceName}`;
    serviceTitle.setAttribute('id', `title-${serviceName}`);

    //Add collapse icon to h3 service name
    const collapseIcon = document.createElement('span');
    collapseIcon.className = '';
    collapseIcon.textContent = '';

    collapseIcon.setAttribute('data-bs-toggle', 'collapse');
    collapseIcon.setAttribute('data-bs-target', `#div-table-content-${serviceName}`);
    collapseIcon.setAttribute('aria-expanded', 'false');
    collapseIcon.setAttribute('aria-controls', `div-table-content-${serviceName}`);

    svg = document.createElementNS("http://www.w3.org/2000/svg", 'svg');
    svg.setAttributeNS(null, "width", "20");
    svg.setAttributeNS(null, "height", "20");
    svg.setAttributeNS(null, "fill", "currentColor");
    svg.setAttributeNS(null, "class", "bi bi-arrows-collapse");
    svg.setAttributeNS(null, "viewBox", "0 0 16 16");

    path = document.createElementNS("http://www.w3.org/2000/svg", 'path');
    path.setAttribute("fill-rule", "evenodd");
    path.setAttribute("d", "M1 8a.5.5 0 0 1 .5-.5h13a.5.5 0 0 1 0 1h-13A.5.5 0 0 1 1 8m7-8a.5.5 0 0 1 .5.5v3.793l1.146-1.147a.5.5 0 0 1 .708.708l-2 2a.5.5 0 0 1-.708 0l-2-2a.5.5 0 1 1 .708-.708L7.5 4.293V.5A.5.5 0 0 1 8 0m-.5 11.707-1.146 1.147a.5.5 0 0 1-.708-.708l2-2a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1-.708.708L8.5 11.707V15.5a.5.5 0 0 1-1 0z");

    svg.append(path)
    collapseIcon.prepend(svg);


    serviceTitle.appendChild(collapseIcon);

    tableDiv.appendChild(serviceTitle);
    dataContainer.appendChild(tableDiv);

    //Add to side menu
    const listService = document.getElementById('list-service');
    if (listService) {
      const listItem = document.createElement('a');
      listItem.className = 'list-group-item list-group-item-action';
      listItem.href = `#div-table-${serviceName}`;
      listItem.textContent = serviceName;
      listService.appendChild(listItem);
    }

    const tableContentDiv = document.createElement('div');
    tableContentDiv.setAttribute('id', `div-table-content-${serviceName}`);
    tableContentDiv.className = 'collapse show collapsed-content';
    tableDiv.appendChild(tableContentDiv);

    Object.keys(resources).forEach((resourceName, index) => {
      const resourceData = resources[resourceName];
      const columns = [];
      // if index >= 0
      if (index > 0) {
        const hr = document.createElement('hr');
        tableContentDiv.appendChild(hr);
      }
      const resourceTitle = document.createElement('h4');
      resourceTitle.className = 'float-start';
      resourceTitle.textContent = `${serviceName} - ${resourceName}`;
      tableContentDiv.appendChild(resourceTitle);

      if (resourceData.length === 0) {
        const emptyMessage = document.createElement('p');
        emptyMessage.textContent = `No data available for ${resourceName}`;
        resourceTitle.className = '';
        tableContentDiv.appendChild(emptyMessage);
        return;
      }

      if (columns.length === 0) {
        // Dynamically create columns based on keys of the first object
        // Merge all keys from all objects to handle missing keys
        const allKeys = new Set();
        resourceData.forEach(item => {
          Object.keys(item).forEach(key => allKeys.add(key));
        });
        allKeys.forEach(key => {
          columns.push({
            field: key,
            title: key.charAt(0).toUpperCase() + key.slice(1),
            sortable: true
          });
        });
      }

      const resourceTable = document.createElement('table');
      resourceTable.setAttribute('id', `table-${serviceName}-${resourceName}`);
      resourceTable.setAttribute('data-virtual-scroll', 'true');
      resourceTable.setAttribute('data-height', '400');
      resourceTable.setAttribute('data-show-columns', 'true');
      resourceTable.setAttribute('data-total-field', "count");
      tableContentDiv.appendChild(resourceTable);

      // if ressource data is dict or array 
      resourceData.forEach(item => {
        Object.keys(item).forEach(key => {
          if (typeof item[key] === 'object') {
            item[key] = JSON.stringify(item[key]);
          }
        });
      });

      $(`#table-${serviceName}-${resourceName}`).bootstrapTable({
        data: resourceData,
        columns: columns,
        search: true,
      });
      resourceTable.className = 'table table-striped';

    });

  });



  const dataSpyList = document.querySelectorAll('[data-bs-spy="scroll"]')
  dataSpyList.forEach(dataSpyEl => {
    bootstrap.ScrollSpy.getInstance(dataSpyEl).refresh()
  })


}