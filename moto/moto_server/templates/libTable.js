window.addEventListener('DOMContentLoaded', function () {
  refreshTable();
});

const refreshData = async () => {
  await fetch('/moto-api/data.json')
    .then(result => result.json())
    .then(data => {
      updateTable(data);
      $('.onbootonly').each(function () {
        this.className = 'tab-pane';
      });
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

  //create menu
  const listService = document.getElementById('list-service');
  if (listService) {
    Object.keys(data).forEach((serviceName, svcIndex) => {
      //Add services to side menu
      const listItem = document.createElement('li');
      listItem.className = 'nav-item';

      const listItemLink = document.createElement('button');
      listItemLink.className = 'nav-link';
      listItemLink.setAttribute('id', `service-tab-${serviceName}`);
      listItemLink.setAttribute('data-bs-toggle', 'pill');
      listItemLink.setAttribute('data-bs-target', `#div-table-${serviceName}`);
      listItemLink.setAttribute('role', 'tab');
      listItemLink.setAttribute('aria-controls', `div-table-${serviceName}`);
      listItemLink.setAttribute('type', 'button');
      if (svcIndex == 0) {
        listItemLink.setAttribute('aria-selected', 'true');
        listItemLink.classList.add('active');
        focusedService = serviceName;
      } else {
        listItemLink.setAttribute('aria-selected', 'false');
      }
      listItemLink.textContent = serviceName;
      listItem.appendChild(listItemLink);
      listService.appendChild(listItem);

    });
  }

  // Clear existing content
  dataContainer.innerHTML = '';

  // Iterate through each service
  // Each service is a div
  // inside this div, each resource is a table if the resource array is not empty

  Object.keys(data).forEach((serviceName) => {
    const resources = data[serviceName];
    //create table object
    const serviceDiv = document.createElement('div');
    serviceDiv.setAttribute('id', `div-table-${serviceName}`);
    if (serviceName == focusedService) {
      serviceDiv.className = 'tab-pane show active firsttab';
    } else {
      serviceDiv.className = 'tab-pane show active onbootonly';
    }
    serviceDiv.setAttribute('role', 'tabpanel');
    serviceDiv.setAttribute('aria-labelledby', `service-tab-${serviceName}`);
    serviceDiv.setAttribute('tabindex', "0");


    //Add horizontal line before each service
    const hr = document.createElement('hr');
    hr.className = 'border border-primary border-1 opacity-75';
    serviceDiv.appendChild(hr);

    //Create a Div for the resources
    const resourcesDiv = document.createElement('div');
    resourcesDiv.setAttribute('id', `div-table-content-${serviceName}`);

    // Append elements title + table
    serviceDiv.appendChild(resourcesDiv);
    dataContainer.appendChild(serviceDiv);

    // Iterate through each resource
    Object.keys(resources).forEach((resourceName, index) => {
      const resourceData = resources[resourceName];
      const columns = [];

      // If not the first resource, add a horizontal line
      if (index > 0) {
        const hr = document.createElement('hr');
        resourcesDiv.appendChild(hr);
      }

      //Create resource title
      const resourceTitle = document.createElement('h4');
      resourceTitle.className = 'float-start mt-3';
      resourceTitle.textContent = `${serviceName} - ${resourceName}`;
      resourcesDiv.appendChild(resourceTitle);

      // If resource data is empty, show a message instead of a table
      if (resourceData.length === 0) {
        const emptyMessage = document.createElement('p');
        emptyMessage.textContent = `No data available for ${resourceName}`;
        emptyMessage.className = 'fst-italic';
        //Remove float class as no table will be shown
        resourceTitle.className = '';
        resourcesDiv.appendChild(emptyMessage);
        return;
      }


      // Dynamically create columns based on keys of the first object
      // Merge all keys from all objects to handle missing keys
      if (columns.length === 0) {
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

      // Create table element
      const resourceTable = document.createElement('table');
      resourceTable.setAttribute('id', `table-${serviceName}-${resourceName}`);
      resourceTable.setAttribute('tabindex', "0");
      resourceTable.setAttribute('data-virtual-scroll', 'true');
      resourceTable.setAttribute('data-height', '400');
      resourceTable.setAttribute('data-show-columns', 'true');
      resourceTable.setAttribute('data-total-field', "count");
      resourcesDiv.appendChild(resourceTable);

      // if resource data is dict or array, convert to string
      resourceData.forEach(item => {
        Object.keys(item).forEach(key => {
          if (typeof item[key] === 'object') {
            item[key] = JSON.stringify(item[key]);
          }
        });
      });

      // Initialize Bootstrap Table
      $(`#table-${serviceName}-${resourceName}`).bootstrapTable({
        data: resourceData,
        columns: columns,
        search: true,
      });

      // Add Bootstrap table classes
      resourceTable.className = 'table table-striped';
    });
  });
}