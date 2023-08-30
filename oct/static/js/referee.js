import { createDropdownItem, clearChildren } from "./util.js"

const matchDropdown = document.getElementById("match-dropdown");
const mapDropdown = document.getElementById("map-dropdown");
const mapDropdownContainer = document.getElementById("map-dropdown-container");
const banDropdown = document.getElementById("ban-dropdown");
const banDropdownContainer = document.getElementById("ban-dropdown-container");
const pickDropdown = document.getElementById("pick-dropdown");
const pickDropdownContainer = document.getElementById("pick-dropdown-container");

const matchInfoContainer = document.getElementById("match-info");
const team1Name = document.getElementById("team-1-name");
const team2Name = document.getElementById("team-2-name");
const matchTime = document.getElementById("match-time");
const mpMake = document.getElementById("mp-make");
const team1Captain = document.getElementById("team-1-captain");
const team2Captain = document.getElementById("team-2-captain");
const mpMods = document.getElementById("mp-mods");
const mpMap = document.getElementById("mp-map");
const mpScore = document.getElementById("mp-score");

const resultContainer = document.getElementById("result-container");
const resultBox = document.getElementById("result-box");
const setBanBtn = document.getElementById("set-ban-button");
const clearBansBtn = document.getElementById("clear-bans-button");
const mpLinkInput = document.getElementById("mp-link-input");
const updateBtn = document.getElementById("update-button");

const bans = [];
const picks = [];
var firstBan = null;
var firstPick = null;
var team1Points = 0;
var team2Points = 0;

var matchInfo = null;
var mappool = null;
var mappoolRound = null;
var currentMap = null;
var team1 = null;
var team2 = null;
var osuMatchId = null;

function makeRequest(path) {
    return fetch("api/"+path)
        .then((resp) => {
            if (!resp.ok) {
                console.log(`Failed request to ${path}`);
                console.log(resp);
                return null;
            }
            return resp.json();
        });
}

function getBeatmapMod(beatmapId) {
    if (mappool == null)  return null;
    for (const map of mappool) {
        if (map.beatmap_id == beatmapId) {
            return map.modification;
        }
    }
}

function getPlayerFromTeam(team, userId) {
    for (const player of team.players) {
        if (player.user.osu_id == userId) {
            return player;
        }
    }
}

function getPlayerInfo(userId) {
    var team = 0;
    var player = getPlayerFromTeam(team1, userId);
    if (player == null) {
        team = 1;
        player = getPlayerFromTeam(team2, userId);
        if (player == null) {
            console.log("Unable to find player in list of teams...");
            return null;
        }
    }
    return {team: team, tier: player.tier};
}

function getScoreMultiplier(bmMod, userMods) {
    if (userMods.includes("EZ") && !bmMod.startsWith("EZ")) return 1.75;
    if (userMods.includes("HR") && !bmMod.startsWith("HR") && !bmMod.startsWith("FM")) return 1.2;
    return 1.0;
}

function updateMpScore() {
    if (firstPick == null) return;
    var subText = team1Points == 7 || team2Points == 7 ? (team1Points == 7 ? `${team1.name} wins, GGs!`:`${team2.name} wins, GGs!`) : ((picks.length+firstPick) % 2 == 0 ? `Next pick: ${team1.name}`:`Next pick: ${team2.name}`);
    mpScore.innerHTML = `${team1.name} | ${team1Points} - ${team2Points} | ${team2.name} // ${subText}`;
}

function onBanMap(evt) {
    if (currentMap == null || firstBan == null) return;
    if (bans.length < 4) {
        const mapLabel = document.getElementById("result-map-"+bans.length);
        const teamLabel = document.getElementById("result-team-"+bans.length);
        const banningTeam = (bans.length + firstBan) % 2 == 0 ? team1 : team2;

        bans.push(currentMap.modification);
        mapLabel.innerHTML = currentMap.modification;
        teamLabel.innerHTML = banningTeam.name;
        return;
    }
}

function onClearBans(evt) {
    while (bans.pop() != undefined) {}
    const match = /result-((map)|(team))-[0-3]/;
    for (var i=0; i<resultBox.children.length; i++) {
        const child = resultBox.children[i];
        if (match.test(child.id)) {
            child.innerHTML = "...";
        }
    }
}

function onMpLinkInput(evt) {
    const validMpLink = /https:\/\/osu\.ppy\.sh\/community\/matches\/([0-9]+)/;
    const match = mpLinkInput.value.match(validMpLink);
    if (match == null) {
        mpLinkInput.style.outlineColor = "red";
        osuMatchId = null;
        return;
    }
    mpLinkInput.style.outlineColor = "green";
    mpLinkInput.style.borderColor = "black";
    osuMatchId = parseInt(match[1]);
}

function createResultItem(text, win) {
    const elm = document.createElement("p");
    elm.classList.add("grid-item");
    elm.style.backgroundColor = win ? "#31f14b":"#f52f31";
    elm.innerHTML = text;
    resultBox.appendChild(elm);
}

function addNewResult(map, pickingTeam, team1Score, team2Score) {
    const team = pickingTeam == 0 ? team1.name : team2.name;
    const win = (pickingTeam == 0 && team1Score > team2Score) || (pickingTeam == 1 && team2Score > team1Score);
    if (team1Score > team2Score) {
        team1Points += 1;
    } else {
        team2Points += 1;
    }
    createResultItem("Pick", win);
    createResultItem(map, win);
    createResultItem(team, win);
    createResultItem(team1Score, win);
    createResultItem(team2Score, win);
    updateMpScore();
}

var updateDebounce = false;
function onUpdate(evt) {
    if (osuMatchId == null || firstPick == null || updateDebounce) return;
    updateDebounce = true;
    setTimeout(()=>{updateDebounce=false}, 5000);
    makeRequest(`osu/matchinfo?match_id=${osuMatchId}`).then((data) => {
        for (const event of data.events) {
            if (event.game == null) continue;
            const game = event.game;
            const bmMod = getBeatmapMod(game.beatmap_id);
            if (bmMod == null || picks.includes(bmMod) || game.scores.length < 4) continue;
            
            var team1Score = 0;
            var team2Score = 0;
            var team1Tier = 0;
            var team2Tier = 0;
            for (const score of game.scores) {
                const player = getPlayerInfo(score.user_id);
                if (player == null) return;
                if (player.team == 0) {
                    const addScore = Math.round(score.score * getScoreMultiplier(bmMod, score.mods));
                    team1Score += addScore;
                    team1Tier += 68-player.tier.charCodeAt(0);
                } else {
                    const addScore = Math.round(score.score * getScoreMultiplier(bmMod, score.mods));
                    team2Score += addScore;
                    team2Tier += 68-player.tier.charCodeAt(0);
                }
            }

            const pickingTeam = (picks.length + firstPick) % 2;
            picks.push(bmMod);

            if (team1Tier == team2Tier || bmMod.startsWith("TB")) {
                addNewResult(bmMod, bmMod.startsWith("TB") ? (team1Score > team2Score ? 0 : 1) : pickingTeam, team1Score, team2Score);
                continue;
            }
            
            const multiplier = 1 - (((team1Tier > team2Tier && pickingTeam == 0) || (team2Tier > team1Tier && pickingTeam == 1)) ? 0.15 : 0.08) * Math.abs(team1Tier - team2Tier);
            if (team1Tier > team2Tier) {
                team1Score *= multiplier;
                team1Score = Math.round(team1Score);
            } else {
                team2Score *= multiplier;
                team2Score = Math.round(team2Score);
            }

            addNewResult(bmMod, pickingTeam, team1Score, team2Score);
        }
    });
}

function onMappoolReturn(data) {
    if (data == null) {
        console.log("Unable to retrieve mappool info");
        return;
    }
    mappool = data;
    data.forEach((beatmap) => {
        const dropdownItem = createDropdownItem(mapDropdown, beatmap.modification);
        dropdownItem.addEventListener("click", (evt) => {
            currentMap = beatmap;
            mpMods.innerHTML = "!mp mods freemod" + (beatmap.modification.startsWith("DT") ? " dt":"");
            mpMap.innerHTML = "!mp map "+beatmap.beatmap_id;
        });
    });
}

function onMatchChosen() {
    const team1Id = parseInt(matchInfo.team_order.split(",")[0]);
    team1 = matchInfo.teams[0].id == team1Id ? matchInfo.teams[0] : matchInfo.teams[1];
    team2 = team1.id == matchInfo.teams[0].id ? matchInfo.teams[1] : matchInfo.teams[0];
    if (team1 != undefined && team2 != undefined) {
        mpMake.innerHTML = "!mp make OCT4: ("+team1.name+") vs ("+team2.name+")";
    }
    team1Name.innerHTML = team1 == null ? "TBD" : team1.name;
    team2Name.innerHTML = team2 == null ? "TBD" : team2.name;
    matchTime.innerHTML = matchInfo.starting_time == null ? "No scheduled time" : matchInfo.starting_time;
    team1Captain.innerHTML = "!mp invite" + (team1 == null ? "" : " "+team1.players[0].user.osu_username);
    team2Captain.innerHTML = "!mp invite" + (team2 == null ? "" : " "+team2.players[0].user.osu_username);

    clearChildren(banDropdownContainer);
    clearChildren(pickDropdownContainer);
    const team1BanItem = createDropdownItem(banDropdown, team1.name);
    const team2BanItem = createDropdownItem(banDropdown, team2.name);
    team1BanItem.addEventListener("click", (evt) => {firstBan = 0;});
    team2BanItem.addEventListener("click", (evt) => {firstBan = 1;});
    const team1PickItem = createDropdownItem(pickDropdown, team1.name);
    const team2PickItem = createDropdownItem(pickDropdown, team2.name);
    team1PickItem.addEventListener("click", (evt) => {firstPick = 0;updateMpScore();});
    team2PickItem.addEventListener("click", (evt) => {firstPick = 1;updateMpScore();});

    matchInfoContainer.style.display = "grid";

    if (mappoolRound == null || mappoolRound != matchInfo.tournament_round.name) {
        mappoolRound = matchInfo.tournament_round.name;
        clearChildren(mapDropdownContainer);
        mapDropdown.removeAttribute("hidden");
        banDropdown.removeAttribute("hidden");
        pickDropdown.removeAttribute("hidden");
        resultContainer.removeAttribute("hidden");
        makeRequest("tournaments/OCT4/"+matchInfo.tournament_round.name+"/mappool").then(onMappoolReturn);
    }
}

export function init() {
    setBanBtn.addEventListener("click", onBanMap);
    clearBansBtn.addEventListener("click", onClearBans);
    mpLinkInput.addEventListener("input", onMpLinkInput);
    updateBtn.addEventListener("click", onUpdate);
    makeRequest("tournaments/OCT4/matches")
        .then((data) => {
            if (data == null) {
                console.log("Unable to retrive match info");
                return;
            }
            data.forEach((match) => {
                // if (match.finished) return;
                
                const dropdownItem = createDropdownItem(matchDropdown, "M"+match.match_id);
                dropdownItem.addEventListener("click", (evt) => {
                    matchInfo = match;
                    onMatchChosen();
                });
            });
        });
}
