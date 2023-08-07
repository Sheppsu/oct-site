var mappool = null;

    function fetchMappool() {
        return fetch("http://127.0.0.1:8000/api/tournaments/oct3/qf/mappool")
            .then((response) => {
                if (response.ok) {return response.json();}
            })
            .then((data) => {
                mappool = data;
            })
    }

    const modFlags = {
        "nm": "1",
        "hd": "9",
        "hr": "17",
        "dt": "65",
        "fm": "0",
    }

    const map_list_container = document.getElementById("map-list-container");
    var dropdown_open = false;

    var playerDropdownIds = {}
    var selectedPlayers = {}
    var selectedMaps = []

    const players = {
        "redPlayers": {
            "1": {
                "regularName": "Player 1",
                "lowercaseName": "player1",
            },
            "2": {
                "regularName": "Player 2",
                "lowercaseName": "player2"
            }
        },
        "bluePlayers": {
            "1": {
                "regularName": "Player 3",
                "lowercaseName": "player3",
            },
            "2": {
                "regularName": "Player 4",
                "lowercaseName": "player4",
            }
        }
    }


    function show_dropdown(id) {
        if (dropdown_open == true) {
            hideAllDropdowns();
        }
        console.log('what')
        document.getElementById(id+"-content").classList.toggle("dropdown-show");
        dropdown_open = true;
    }

    function hideAllDropdowns() {
        var dropdowns = document.getElementsByClassName("dropdown-content");
            var i;
            for (i = 0; i < dropdowns.length; i++) {
                var openDropdown = dropdowns[i];
                if (openDropdown.classList.contains('dropdown-show')) {
                    openDropdown.classList.remove('dropdown-show');
                }
            }
        dropdown_open = false;
    }

    function onPlayerClick(event) {
        event.preventDefault();
        splitId = event.target.id.split("-"); // ['map', '1', 'player', '1', 'red', 'box', '1', 'dropdown', 'item'] (example)
        playerBox = document.getElementById(splitId[0] + "-" + splitId[1] + "-" + splitId[4] + "-player-" + splitId[6] + "-text");

        if (selectedPlayers[splitId[1]][splitId[4]].includes(playerBox.textContent)) { // remove currently selected player from selectedplayer array
            selectedPlayers[splitId[1]][splitId[4]] = selectedPlayers[splitId[1]][splitId[4]].filter(str => str !== playerBox.textContent);
        }
        selectedPlayers[splitId[1]][splitId[4]].push(players[`${splitId[4]}Players`][splitId[3]]["regularName"]);
        playerBox.textContent = players[`${splitId[4]}Players`][splitId[3]]["regularName"];

        var a = "map-" + splitId[1] + "-";
        addPlayersToDropdowns(a);
    }

    function onMapClick(event) {
        event.preventDefault();
        splitId = event.target.id.split("-"); // ['map', '1', 'NM2', 'dropdown', 'item']
        mapText = document.getElementById("map-" +  splitId[1] + "-beatmap-text");
        mapModsText = document.getElementById("map-" + splitId[1] + "-beatmap-mods-command");
        mapIdText = document.getElementById("map-" + splitId[1] + "-beatmap-id-command");
        mapTitle = document.getElementById("map-" + splitId[1] + "-beatmap-title");
        mapDifficulty = document.getElementById("map-" + splitId[1] + "-beatmap-difficulty");
        
        selectedMaps.push(splitId[2]);
        mapText.textContent = splitId[2];
        mapModsText.textContent = `!mp mods ${modFlags[splitId[2].substring(0, 2).toLowerCase()]}`;

        for (x in mappool) {
            if (mappool[x]["modification"] == splitId[2]) {
                mapTitle.textContent = `${mappool[x]['artist']} - ${mappool[x]['title']}`;
                mapIdText.textContent = `!mp map ${mappool[x]['beatmap_id']}`;
                mapDifficulty.textContent = `[${mappool[x]['difficulty']}]`
            }
        }
        addMapsToDropdown(`map-${splitId[1]}-`);

    }
    function addMapsToDropdown(map) {
        mapBox = document.getElementById(`${map}beatmap-dropdown-content`);
        mapBox.innerHTML = "";
        for (x in mappool) {
            if (selectedMaps.includes(mappool[x])) {
                console.log('yep')
                continue;
            }
            else {
                console.log('nop')
            }

            a = document.createElement('a');
            a.href = '#';
            a.innerHTML = mappool[x]["modification"];
            a.id = map + mappool[x]["modification"] + "-dropdown-item";
            mapBox.addEventListener('click', onMapClick);

            mapBox.appendChild(a);
        }
    }

    function addPlayersToDropdowns(map) {
        if (playerDropdownIds.hasOwnProperty(map)) {
            for (x in playerDropdownIds[map]) {
                a = document.getElementById(playerDropdownIds[map][x]);
                a.remove();
            }
            playerDropdownIds[map] = [];
        } else {
            playerDropdownIds[map] = [];
        }

        rp1 = document.getElementById(`${map}red-player-1-dropdown-content`);
        rp2 = document.getElementById(`${map}red-player-2-dropdown-content`);
        bp1 = document.getElementById(`${map}blue-player-1-dropdown-content`);
        bp2 = document.getElementById(`${map}blue-player-2-dropdown-content`);
        
        for (i in players["redPlayers"]) {
            if (selectedPlayers[map.split("-")[1]]["red"].includes(players["redPlayers"][i]["regularName"])) {
                continue;
            }
            a = document.createElement('a');
            a.href = '#';
            a.innerHTML = players["redPlayers"][i]["regularName"];
            a.id = map + "player-" + i + "-red-box-1-dropdown-item";
            playerDropdownIds[map].push(a.id);
            rp1.addEventListener('click', onPlayerClick);

            a2 = document.createElement('a');
            a2.href = '#';
            a2.innerHTML = players["redPlayers"][i]["regularName"];
            a2.id = map + "player-" + i + "-red-box-2-dropdown-item";
            playerDropdownIds[map].push(a2.id);
            rp2.addEventListener('click', onPlayerClick);

            rp1.appendChild(a);
            rp2.appendChild(a2);
        }

        for (i in players["bluePlayers"]) {
            if (selectedPlayers[map.split("-")[1]]["blue"].includes(players["bluePlayers"][i]["regularName"])) {
                continue;
            }
            a = document.createElement('a');
            a.href = '#';
            a.innerHTML = players["bluePlayers"][i]["regularName"];
            a.id = map + "player-" + i + "-blue-box-1-dropdown-item";
            playerDropdownIds[map].push(a.id);
            bp1.addEventListener('click', onPlayerClick);

            a2 = document.createElement('a');
            a2.href = '#';
            a2.innerHTML = players["bluePlayers"][i]["regularName"];
            a2.id = map + "player-" + i + "-blue-box-2-dropdown-item";
            playerDropdownIds[map].push(a2.id);
            bp2.addEventListener('click', onPlayerClick);

            bp1.appendChild(a);
            bp2.appendChild(a2);
        }
    }


    function generateMap(map_number) {
        const map = "map-" + map_number + "-";
        var map_html_string = 
                    /*html*/`<div class="map-container">
                        <div class="map-selector">
                            <div id="${map}beatmap-dropdown" class="dropdown">
                                <div id="${map}beatmap-dropdown-content" class="dropdown-content prevent-select">
                                    
                                </div>
                            </div>
                            <div style="width: 15%; height: 100%; display: flex; align-items: center; justify-content: center; margin-left: 15px;">
                                <span class="material-symbols-outlined prevent-select" id="${map}beatmap-dropdown" onclick="show_dropdown(this.id)">expand_more</span>
                                <p id="${map}beatmap-text" style="font-size: 30px; font-weight: 400; margin-left: 5px;">Map</p>
                            </div>
                            <div class="map-commands">
                                <div style="display: flex; width: 100%; height: 100%; align-items: center; justify-content: center;">
                                    <div style="display: flex; width: 70%; height: 100%; justify-content: center; flex-direction: column; padding: 5px">
                                        <p id="${map}beatmap-title" style="font-weight: bold;"></p>
                                        <p id="${map}beatmap-difficulty"></p>
                                    </div>
                                    <div style="display: flex; width: 30%; height: 100%; flex-direction: column; align-items: center; justify-content: center;">
                                        <p id="${map}beatmap-mods-command">!mp mods ?</p>
                                        <p id="${map}beatmap-id-command">!mp map ?</p>
                                    </div>
                                </div>
                            </div>  
                        </div>
                        <div class="map-winner">
                              
                        </div>
                    </div>
                    <div class="players-container">
                        <div class="red-team-player-container">
                            <div id="${map}red-player-1" class="player-container">
                                <div id="${map}red-player-1-dropdown" class="dropdown">
                                    <div id="${map}red-player-1-dropdown-content" class="dropdown-content prevent-select"></div>
                                </div>
                                <div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                                    <span class="material-symbols-outlined prevent-select" id="${map}red-player-1-dropdown" onclick="show_dropdown(this.id)">expand_more</span>
                                    <p id="${map}red-player-1-text" class="prevent-select">Select</p>
                                </div>
                            </div>
                            <div id="${map}red-player-2"" class="player-container">
                                <div id="${map}red-player-2-dropdown" class="dropdown">
                                    <div id="${map}red-player-2-dropdown-content" class="dropdown-content prevent-select"></div>
                                </div>
                                <div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                                    <span class="material-symbols-outlined prevent-select" id="${map}red-player-2-dropdown" onclick="show_dropdown(this.id)">expand_more</span>
                                    <p id="${map}red-player-2-text" class="prevent-select">Select</p>
                                </div>
                            </div>
                            
                        </div>
                        <div class="tier-value-container">
                            <p>Tier Value</p>
                            <h1>7</h1>
                        </div>
                        <div class="blue-team-player-container">
                            <div id="${map}blue-player-1"" class="player-container">
                                <div id="${map}blue-player-1-dropdown" class="dropdown">
                                    <div id="${map}blue-player-1-dropdown-content" class="dropdown-content prevent-select"></div>
                                </div>
                                <div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                                    <span class="material-symbols-outlined prevent-select" id="${map}blue-player-1-dropdown" onclick="show_dropdown(this.id)">expand_more</span>
                                    <p id="${map}blue-player-1-text" class="prevent-select">Select</p>
                                </div>
                            </div>
                            <div id="${map}blue-player-2"" class="player-container">
                                <div id="${map}blue-player-2-dropdown" class="dropdown">
                                    <div id="${map}blue-player-2-dropdown-content" class="dropdown-content prevent-select"></div>
                                </div>
                                <div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                                    <span class="material-symbols-outlined prevent-select" id="${map}blue-player-2-dropdown" onclick="show_dropdown(this.id)">expand_more</span>
                                    <p id="${map}blue-player-2-text" class="prevent-select">Select</p>
                                </div>
                            </div>
                        </div>
                    </div>`;
        // add dictionary items for the selected player slots
        selectedPlayers[map.split("-")[1]] = {};
        selectedPlayers[map.split("-")[1]]["red"] = [];
        selectedPlayers[map.split("-")[1]]["blue"] = [];
        

        var map_div = document.createElement('div');
        map_div.classList.add('map-players-container');

        map_div.innerHTML = map_html_string;
        map_list_container.appendChild(map_div);
        addPlayersToDropdowns(map);
        addMapsToDropdown(map);
    }

    window.onclick = function(event) {
        if (!event.target.matches('.material-symbols-outlined')) {
            hideAllDropdowns();
        }
    }   
    window.onload = function() {
        fetchMappool().then(() => {
            for (let i = 1; i < 11; i++) {
                generateMap(i);
            }
        })
    }