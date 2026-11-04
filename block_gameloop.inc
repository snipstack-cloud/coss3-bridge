      [*] = ;   // === BRIDGE LOOP: episode control, game side ===
      [*] = ;   // Lives here and not in the interface actor: reading files compiles
      [*] = ;   // only on this side. The interface is reached through GUIExecuteState,
      [*] = ;   // the same way lib/miscext3.script does it.
      [*] = ;   if (plind = GetPlayerIndexInterfaceIO) and (not _net_IsClient) and (not _net_IsReplay) then
      [*] = ;   begin
      [*] = ;      // NEW MATCH BY THE CLOCK (5.11, mac, item 3 of the block list; live games 2 and 3 of 4.11). A match started from the
      [*] = ;      // game menu sends no NEW, and br_hdef/br_hkite/br_hbal outlived the previous match: the defence reflex read 'on' from
      [*] = ;      // the first tick with nobody near, holds were stripped all game, the fist stood while recruits piled at the barracks.
      [*] = ;      // Game time running backwards means a new match: every parser of ours that remembers a match is cleared here, before
      [*] = ;      // the state and command blocks of this tick, and it is said aloud once. The first tick ever creates the clock only.
      [*] = ;      var brmp : Integer = ParserSelectByKey('br_match');
      [*] = ;      var brmnow : Float = GetGameTime;
      [*] = ;      var brmlast : Float = -1;
      [*] = ;      if (brmp = 0) then
      [*] = ;      brmp := ParserCreate('br_match')
      [*] = ;      else
      [*] = ;      brmlast := ParserGetFloatValueByKeyByHandle(brmp, 'gt');
      [*] = ;      if (brmlast >= 0) and (brmnow < brmlast - 2.0) then
      [*] = ;      begin
      [*] = ;      var brmq : Integer;
      [*] = ;      brmq := ParserSelectByKey('br_hgrp');
      [*] = ;      if (brmq <> 0) then ParserClearByHandle(brmq);
      [*] = ;      brmq := ParserSelectByKey('br_hwave');
      [*] = ;      if (brmq <> 0) then ParserClearByHandle(brmq);
      [*] = ;      brmq := ParserSelectByKey('br_kills');
      [*] = ;      if (brmq <> 0) then ParserClearByHandle(brmq);
      [*] = ;      brmq := ParserSelectByKey('br_hstate');
      [*] = ;      if (brmq <> 0) then ParserClearByHandle(brmq);
      [*] = ;      brmq := ParserSelectByKey('br_hfail');
      [*] = ;      if (brmq <> 0) then ParserClearByHandle(brmq);
      [*] = ;      brmq := ParserSelectByKey('br_hlog');
      [*] = ;      if (brmq <> 0) then ParserClearByHandle(brmq);
      [*] = ;      brmq := ParserSelectByKey('br_hdef');
      [*] = ;      if (brmq <> 0) then ParserClearByHandle(brmq);
      [*] = ;      brmq := ParserSelectByKey('br_hkite');
      [*] = ;      if (brmq <> 0) then ParserClearByHandle(brmq);
      [*] = ;      brmq := ParserSelectByKey('br_hbal');
      [*] = ;      if (brmq <> 0) then ParserClearByHandle(brmq);
      [*] = ;      Log('bridge-human: NEW MATCH by the clock at ' + IntToStr(Round(brmnow)) + ' s (last seen ' + IntToStr(Round(brmlast)) + ' s) - memory of the previous match cleared');
      [*] = ;      end;
      [*] = ;      ParserSetFloatValueByKeyByHandle(brmp, 'gt', brmnow);
      [*] = ;      var hhb : Integer = ParserSelectByKey('br_hb');
      [*] = ;      var brhblast : Integer = -1000;
      [*] = ;      if (hhb = 0) then
      [*] = ;      hhb := ParserCreate('br_hb')
      [*] = ;      else
      [*] = ;      brhblast := ParserGetIntValueByKeyByHandle(hhb, 'realtime');
      [*] = ;      var brhbnow : Integer = Round(_misc_GetRealTime);
      [*] = ;      if ((brhbnow-brhblast) >= 5) or (brhbnow < brhblast) then
      [*] = ;      begin
      [*] = ;         ParserClearByHandle(hhb);
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'realtime', brhbnow);
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'gametime', Round(GetGameTime));
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'myplind', plind);
      [*] = ;         ParserSetIntValueByKeyByHandle(hhb, 'victory', gPlayer[plind].victorystate);
      [*] = ;         // STAGE OF THE STATE BLOCK (29.10 night, mac, after D22/D23): the state block marks how far it got in
      [*] = ;         // br_hstate (stage<plind> 0..11, 11 = saved; stageat = game time of the entry). Copied into the pulse,
      [*] = ;         // because this parser is cleared before every save and the state block runs after us in the tick.
      [*] = ;         var hhbs : Integer = ParserSelectByKey('br_hstate');
      [*] = ;         if (hhbs <> 0) then
      [*] = ;         begin
      [*] = ;            var hhbi : Integer;
      [*] = ;            for hhbi := 0 to gc_MaxPlayerCount-1 do
      [*] = ;            begin
      [*] = ;               if (ParserGetValueByKeyByHandle(hhbs, 'stage' + IntToStr(hhbi)) <> '') then
      [*] = ;               begin
      [*] = ;                  ParserSetIntValueByKeyByHandle(hhb, 'hs_stage' + IntToStr(hhbi), ParserGetIntValueByKeyByHandle(hhbs, 'stage' + IntToStr(hhbi)));
      [*] = ;                  ParserSetIntValueByKeyByHandle(hhb, 'hs_at' + IntToStr(hhbi), ParserGetIntValueByKeyByHandle(hhbs, 'stageat' + IntToStr(hhbi)));
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         ParserSaveToFileByHandle(hhb, '@@OUT@@coss3_hb.dat');
      [*] = ;      end;
      [*] = ;      var brctlpath : String = '@@OUT@@coss3_ctl.dat';
      [*] = ;      if IsFileExists(brctlpath) then
      [*] = ;      begin
      [*] = ;         var hctl : Integer = ParserSelectByKey('br_ctl');
      [*] = ;         if (hctl = 0) then
      [*] = ;         hctl := ParserCreate('br_ctl');
      [*] = ;         ParserClearByHandle(hctl);
      [*] = ;         var brctlcmd : String;       // must live outside the block below
      [*] = ;         // Match settings for NEW. -1 means 'leave as is', so an old
      [*] = ;         // client that does not send them changes nothing.
      [*] = ;         var brctlres   : Integer = -1;   // gen.resourcestart: 0=1000 1=4000 2=5000
      [*] = ;         var brctlpeace : Integer = -1;   // additional.peacetime, default=0 minutes
      [*] = ;         var brctlai    : Integer = -1;   // aidifficulty: 3 = Impossible
      [*] = ;         // WHICH SLOT THE BOT TAKES (1.10, request of the player). -1 means 'as
      [*] = ;         // before': slot 0 human, slot 1 native ai - that is what all 213 recorded
      [*] = ;         // runs played, and the series must not change under them.
      [*] = ;         // With botslot >= 1 the match becomes HUMAN AGAINST BOT: the player keeps
      [*] = ;         // slot 0 (offline the engine gives the local player slot 0 and nothing else
      [*] = ;         // - showcustomgame.inc:556 writes the profile name there), and the bot gets
      [*] = ;         // its own slot with NO native ai at all. Why it cannot be done from the menu:
      [*] = ;         // offline a slot becomes human only through a network lanid
      [*] = ;         // (showcustomgame.inc:530-537), so the menu offers ai or closed and nothing
      [*] = ;         // else. These fields are written before DoNewGame, which is the one place
      [*] = ;         // where the menu's choice can still be overridden.
      [*] = ;         var brctlbot   : Integer = -1;
      [*] = ;         // The UI list numbers levels from 1 (0 means 'slot open'),
      [*] = ;         // while aidifficulty holds one less: showcustomgame.inc:647
      [*] = ;         // sets the list index to aidifficulty+1. So Impossible is 3.
      [*] = ;         // Names come from locale/en/gui.txt: 0 None, 1 Normal,
      [*] = ;         // 2 Hard, 3 Very Hard, 4 Impossible.
      [*] = ;         var brctlnat   : String;         // country sid, 'net' = Netherlands
      [*] = ;         // THE OPPONENT'S NATION (28.10 defense series, ported to master 29.10 for the Russia game). Empty means
      [*] = ;         // 'same as ours', which is what every recorded run played. Read only by the native-ai branch below.
      [*] = ;         var brctlnat2  : String;
      [*] = ;         // additional.balloon: 0 as usual, 1 forbidden, 2 GIVEN TO ALL.
      [*] = ;         // With 2 the fog of war is off for everyone - _player_UpdateFOW
      [*] = ;         // (player.script:456) skips AddFOWPlayers when balloon=with.
      [*] = ;         // A MATCH SETTING, not a cheat, and it decides whether the bridge
      [*] = ;         // may tell the model what the enemy has: on an open map a human
      [*] = ;         // sees it too.
      [*] = ;         var brctlball  : Integer = -1;
      [*] = ;         // additional.cannons: 1 = no cannons, towers and walls for ANYONE
      [*] = ;         // (player.script:2703 clears bproduceenabled for mortars and guns
      [*] = ;         // and disables the artillery upgrades).
      [*] = ;         var brctlcann  : Integer = -1;
      [*] = ;         // additional.capture: 1 no peasants, 2 no peasants and centres,
      [*] = ;         // 3 artillery only. This one touches our own measure: by default a
      [*] = ;         // peasant can be CAPTURED instead of killed, and he leaves the
      [*] = ;         // enemy count all the same - so 'goal taken' could mean a capture.
      [*] = ;         var brctlcapt  : Integer = -1;
      [*] = ;         // additional.marketdip: 1 no diplomacy, 2 NO MARKET for ANYONE,
      [*] = ;         // 3 neither, 4 expensive mercenaries (showcustomgame.inc:920-925).
      [*] = ;         // Our own bot is barred from the market by --ban, but that key
      [*] = ;         // binds only US: the native AI built one at 1:56-2:51 in every
      [*] = ;         // match measured 20.09, and the market cures exactly our worst
      [*] = ;         // bottleneck - gold, tight in 61-98 per cent of ticks.
      [*] = ;         var brctlmark  : Integer = -1;
      [*] = ;         // additional.century18: 1 forbidden for ANYONE, 2 allowed. The
      [*] = ;         // academy is the door into the 18th century, and the enemy opened
      [*] = ;         // it at 11:24-16:17 in every match. Forbidding the century closes
      [*] = ;         // that door on BOTH sides, which is what makes it fair.
      [*] = ;         var brctlcent  : Integer = -1;
      [*] = ;         // gen.mapsize: 0 -> 320, 1 -> 480, 2 -> 640, 3 -> 256 (donewgame.inc,
      [*] = ;         // 'case gMap.settings.gen.mapsize of'). RULES OF THE HACKATHON ASK FOR
      [*] = ;         // THE SMALL MAP, that is 3. Nobody set it until 27.09, so containers
      [*] = ;         // played whatever the profile kept - mapsize 0, a 320 map - and every
      [*] = ;         // threshold measured in CELLS meant a different distance than written:
      [*] = ;         // a cell is width/16, so 20 units on 320 and 16 on 256.
      [*] = ;         var brctlmapsz : Integer = -1;
      [*] = ;         // GAME SPEED (25.09). The engine has three modes and the factors
      [*] = ;         // live in dmscript.global:1027 - slow 7, normal 10, fast 14 (the
      [*] = ;         // fourth, 20, is commented out there). -1 means DO NOT TOUCH: the
      [*] = ;         // key has been travelling in the control file since the start and
      [*] = ;         // nobody read it, so callers still send 0 - and 0 is the SLOW mode.
      [*] = ;         // Reading it as a mode without this guard would quietly slow every
      [*] = ;         // container game down.
      [*] = ;         var brctlspd  : Integer = -1;
      [*] = ;         if ParserLoadFromFileByHandle(hctl, brctlpath) then
      [*] = ;         begin
      [*] = ;            brctlcmd := ParserGetValueByKeyByHandle(hctl, 'cmd');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'res') <> '') then
      [*] = ;            brctlres := ParserGetIntValueByKeyByHandle(hctl, 'res');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'peace') <> '') then
      [*] = ;            brctlpeace := ParserGetIntValueByKeyByHandle(hctl, 'peace');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'ai') <> '') then
      [*] = ;            brctlai := ParserGetIntValueByKeyByHandle(hctl, 'ai');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'balloon') <> '') then
      [*] = ;            brctlball := ParserGetIntValueByKeyByHandle(hctl, 'balloon');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'cannons') <> '') then
      [*] = ;            brctlcann := ParserGetIntValueByKeyByHandle(hctl, 'cannons');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'capture') <> '') then
      [*] = ;            brctlcapt := ParserGetIntValueByKeyByHandle(hctl, 'capture');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'market') <> '') then
      [*] = ;            brctlmark := ParserGetIntValueByKeyByHandle(hctl, 'market');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'century18') <> '') then
      [*] = ;            brctlcent := ParserGetIntValueByKeyByHandle(hctl, 'century18');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'mapsize') <> '') then
      [*] = ;            brctlmapsz := ParserGetIntValueByKeyByHandle(hctl, 'mapsize');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'speed') <> '') then
      [*] = ;            brctlspd := ParserGetIntValueByKeyByHandle(hctl, 'speed');
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'botslot') <> '') then
      [*] = ;            brctlbot := ParserGetIntValueByKeyByHandle(hctl, 'botslot');
      [*] = ;            brctlnat := ParserGetValueByKeyByHandle(hctl, 'nation');
      [*] = ;            brctlnat2 := ParserGetValueByKeyByHandle(hctl, 'nation2');
      [*] = ;         end;
      [*] = ;         DeleteFileStream(brctlpath);
      [*] = ;         var back : Integer = ParserSelectByKey('br_ack');
      [*] = ;         if (back = 0) then
      [*] = ;         back := ParserCreate('br_ack');
      [*] = ;         ParserClearByHandle(back);
      [*] = ;         ParserSetValueByKeyByHandle(back, 'cmd', brctlcmd);
      [*] = ;         ParserSetIntValueByKeyByHandle(back, 'gametime', Round(GetGameTime));
      [*] = ;         ParserSetIntValueByKeyByHandle(back, 'myplind', plind);
      [*] = ;         ParserSetIntValueByKeyByHandle(back, 'victory', gPlayer[plind].victorystate);
      [*] = ;         ParserSetValueByKeyByHandle(back, 'done', 'ping');
      [*] = ;         if (brctlcmd = 'END') then
      [*] = ;         begin
      [*] = ;            gPlayer[plind].victorystate := gc_player_victorystate_lose;
      [*] = ;            if (gPlayer[plind].victorystategametime = 0) then
      [*] = ;            gPlayer[plind].victorystategametime := GetGameTime;
      [*] = ;            ParserSetValueByKeyByHandle(back, 'done', 'surrendered');
      [*] = ;         end;
      [*] = ;         if (brctlcmd = 'NEW') then
      [*] = ;         begin
      [*] = ;            // Match settings are applied HERE, before DoNewGame. Otherwise
      [*] = ;            // the game keeps whatever was left in the menu, and experiments
      [*] = ;            // become incomparable: on 12.09 that gave 5000 resources instead
      [*] = ;            // of 1000 and an enemy that already had 8 buildings.
      [*] = ;            // Numbers come from the game code, not from guessing:
      [*] = ;            //   resourcestart 0 -> 1000 (initmapgen.inc:167; 1->4000, 2->5000)
      [*] = ;            //   peacetime default -> 0 min (_misc_GetPeaceTime, misc.script:4264)
      [*] = ;            //   player fields -> gMap.players[i] (showcustomgame.inc)
      [*] = ;            if (brctlres >= 0) then
      [*] = ;            gMap.settings.gen.resourcestart := brctlres;
      [*] = ;            if (brctlpeace >= 0) then
      [*] = ;            gMap.settings.additional.peacetime := brctlpeace;
      [*] = ;            if (brctlball >= 0) then
      [*] = ;            gMap.settings.additional.balloon := brctlball;
      [*] = ;            if (brctlcann >= 0) then
      [*] = ;            gMap.settings.additional.cannons := brctlcann;
      [*] = ;            if (brctlcapt >= 0) then
      [*] = ;            gMap.settings.additional.capture := brctlcapt;
      [*] = ;            if (brctlmark >= 0) then
      [*] = ;            gMap.settings.additional.marketdip := brctlmark;
      [*] = ;            if (brctlmapsz >= 0) then
      [*] = ;            gMap.settings.gen.mapsize := brctlmapsz;
      [*] = ;            if (brctlcent >= 0) then
      [*] = ;            gMap.settings.additional.century18 := brctlcent;
      [*] = ;            // Flat ifs on purpose: a case with one-line branches once killed
      [*] = ;            // the tick, and a scalar in a nested begin is the other known trap.
      [*] = ;            //
      [*] = ;            // THE PROFILE MUST BE SET TOO, and this was measured 25.09: setting
      [*] = ;            // only the factor changes what GetTimeSpeedFactor returns AND NOTHING
      [*] = ;            // ELSE, because the map load right after NEW runs
      [*] = ;            // _control_SetGameSpeedByMode(gProfile.igamespeed, True)
      [*] = ;            // (common.inc/onloadfull.inc:120) and restores the profile value over
      [*] = ;            // ours. The receipt looked right (14, then 10) because it is written
      [*] = ;            // before the load; the clock told the truth - 1.40 game seconds per
      [*] = ;            // real second BOTH times. gProfile.igamespeed is what the GUI state
      [*] = ;            // WriteTimeSpeed writes next to the factor, so we write both.
      [*] = ;            if (brctlspd = 0) then
      [*] = ;            begin
      [*] = ;               SetTimeSpeedFactor(gc_settings_gamespeed_0);
      [*] = ;               gProfile.igamespeed := 0;
      [*] = ;            end;
      [*] = ;            if (brctlspd = 1) then
      [*] = ;            begin
      [*] = ;               SetTimeSpeedFactor(gc_settings_gamespeed_1);
      [*] = ;               gProfile.igamespeed := 1;
      [*] = ;            end;
      [*] = ;            if (brctlspd = 2) then
      [*] = ;            begin
      [*] = ;               SetTimeSpeedFactor(gc_settings_gamespeed_2);
      [*] = ;               gProfile.igamespeed := 2;
      [*] = ;            end;
      [*] = ;            // HUMAN AGAINST BOT. Checked FIRST and with an else below, so the path
      [*] = ;            // the 213 recorded runs played is not touched when botslot is absent.
      [*] = ;            if (brctlbot >= 1) then
      [*] = ;            begin
      [*] = ;               // Slot 0 the same careful way as below: only nation and team. The
      [*] = ;               // first version of that code rewrote the slot whole and wiped the
      [*] = ;               // profile name, leaving a nameless player of an 'unknown' nation.
      [*] = ;               if (brctlnat <> '') then
      [*] = ;               gMap.players[0].cid := _country_GetIDBySID(brctlnat);
      [*] = ;               gMap.players[0].team := 1;
      [*] = ;               // The bot's slot: human, and the native ai explicitly OFF. Both
      [*] = ;               // matter. bhuman is what the state and command blocks gate on
      [*] = ;               // (block_hstate.inc:7 takes any player with `not bai`), and bai
      [*] = ;               // False is what keeps the engine's own ai from giving this slot
      [*] = ;               // orders at the same time as we do - two hands on one army.
      [*] = ;               gMap.players[brctlbot].bexists := True;
      [*] = ;               gMap.players[brctlbot].bhuman := True;
      [*] = ;               gMap.players[brctlbot].bai := False;
      [*] = ;               gMap.players[brctlbot].bclosed := False;
      [*] = ;               gMap.players[brctlbot].bready := True;
      [*] = ;               gMap.players[brctlbot].team := 2;
      [*] = ;               // -1 is gc_player_difficulty_none (dmscript.global:781). Written as a
      [*] = ;               // number, not by name: the verifier does not find that constant in the
      [*] = ;               // data it scans, and an unknown name is exactly what it is there to
      [*] = ;               // catch. Difficulty is meaningless on this slot anyway - it belongs to
      [*] = ;               // the native ai, which is off here.
      [*] = ;               gMap.players[brctlbot].aidifficulty := -1;
      [*] = ;               // A name, so the scoreboard says who this is. Safe here, unlike on
      [*] = ;               // slot 0: this slot has no profile to lose.
      [*] = ;               gMap.players[brctlbot].name := 'BRIDGE';
      [*] = ;               // The bot's nation (30.10, Poland game): nation2 when asked for, else the same as the human's -
      [*] = ;               // this branch had only 'nation' and gave Poland to both slots (nat0 = 6, nat1 = 6).
      [*] = ;               if (brctlnat2 <> '') then
      [*] = ;               begin
      [*] = ;                  gMap.players[brctlbot].cid := _country_GetIDBySID(brctlnat2);
      [*] = ;               end
      [*] = ;               else
      [*] = ;               if (brctlnat <> '') then
      [*] = ;               begin
      [*] = ;                  gMap.players[brctlbot].cid := _country_GetIDBySID(brctlnat);
      [*] = ;               end;
      [*] = ;               // Everyone else closed, slot 0 and the bot's aside: a third player
      [*] = ;               // changes the conditions, and a stray native ai would make the
      [*] = ;               // match unlike the one that was asked for.
      [*] = ;               var brpl2 : Integer;
      [*] = ;               for brpl2 := 1 to gc_MaxPlayerCount-1 do
      [*] = ;               if (brpl2 <> brctlbot) then
      [*] = ;               begin
      [*] = ;                  gMap.players[brpl2].bexists := False;
      [*] = ;                  gMap.players[brpl2].bclosed := True;
      [*] = ;               end;
      [*] = ;            end
      [*] = ;            else
      [*] = ;            if (brctlai >= 0) then
      [*] = ;            begin
      [*] = ;               // Do NOT rewrite the human slot as a whole. The first version
      [*] = ;               // set bexists/bhuman/bai/team on it and wiped what the game
      [*] = ;               // puts there from the profile: the name and identity. The slot
      [*] = ;               // became nameless and the nation showed as 'unknown'. The menu
      [*] = ;               // has already set that slot up, so touch only the nation.
      [*] = ;               if (brctlnat <> '') then
      [*] = ;               gMap.players[0].cid := _country_GetIDBySID(brctlnat);
      [*] = ;               gMap.players[0].team := 1;
      [*] = ;               // The opponent slot has to be created in full.
      [*] = ;               gMap.players[1].bexists := True;
      [*] = ;               gMap.players[1].bhuman := False;
      [*] = ;               gMap.players[1].bai := True;
      [*] = ;               gMap.players[1].bclosed := False;
      [*] = ;               gMap.players[1].bready := True;
      [*] = ;               gMap.players[1].team := 2;
      [*] = ;               gMap.players[1].aidifficulty := brctlai;
      [*] = ;               // His nation: nation2 when asked for, else the same as ours.
      [*] = ;               if (brctlnat2 <> '') then
      [*] = ;               begin
      [*] = ;                  gMap.players[1].cid := _country_GetIDBySID(brctlnat2);
      [*] = ;               end
      [*] = ;               else
      [*] = ;               if (brctlnat <> '') then
      [*] = ;               begin
      [*] = ;                  gMap.players[1].cid := _country_GetIDBySID(brctlnat);
      [*] = ;               end;
      [*] = ;               // Close the rest: extra players change the conditions.
      [*] = ;               var brpl : Integer;
      [*] = ;               for brpl := 2 to gc_MaxPlayerCount-1 do
      [*] = ;               begin
      [*] = ;                  gMap.players[brpl].bexists := False;
      [*] = ;                  gMap.players[brpl].bclosed := True;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            // Report what actually happened: without it there is no way to
      [*] = ;            // tell 'was not applied' from 'applied, then overridden'.
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'nat0', gMap.players[0].cid);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'nat1', gMap.players[1].cid);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'ai1', gMap.players[1].aidifficulty);
      [*] = ;            // WHAT BECAME OF THE BOT SLOT, read back from the engine and not from
      [*] = ;            // our own wish. The setup happens before DoNewGame, and the load right
      [*] = ;            // after it has overridden our fields before - that is how the game
      [*] = ;            // speed turned out to be restored from the profile on 25.09. Reporting
      [*] = ;            // the WISH would have hidden it; reporting the fields tells the truth.
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'botslot', brctlbot);
      [*] = ;            if (brctlbot >= 1) then
      [*] = ;            begin
      [*] = ;               ParserSetBoolValueByKeyByHandle(back, 'bot_human', gMap.players[brctlbot].bhuman);
      [*] = ;               ParserSetBoolValueByKeyByHandle(back, 'bot_ai', gMap.players[brctlbot].bai);
      [*] = ;               ParserSetBoolValueByKeyByHandle(back, 'bot_exists', gMap.players[brctlbot].bexists);
      [*] = ;               ParserSetIntValueByKeyByHandle(back, 'bot_team', gMap.players[brctlbot].team);
      [*] = ;               ParserSetIntValueByKeyByHandle(back, 'bot_nat', gMap.players[brctlbot].cid);
      [*] = ;               ParserSetIntValueByKeyByHandle(back, 'my_team', gMap.players[0].team);
      [*] = ;            end;
      [*] = ;            ParserSetValueByKeyByHandle(back, 'done', 'newgame_called');
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'res', gMap.settings.gen.resourcestart);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'peace', gMap.settings.additional.peacetime);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'balloon', gMap.settings.additional.balloon);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'cannons', gMap.settings.additional.cannons);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'capture', gMap.settings.additional.capture);
      [*] = ;            // Echo the new settings back: without it the match terms can
      [*] = ;            // only be checked indirectly - by whether the enemy built a
      [*] = ;            // market. On 20.09 that meant waiting until 4:20 game time.
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'market', gMap.settings.additional.marketdip);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'century18', gMap.settings.additional.century18);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'mapsize', gMap.settings.gen.mapsize);
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'speed', floor(GetTimeSpeedFactor));
      [*] = ;            ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;            // MEMORY OF THE MATCH DIES WITH THE MATCH (5.10, par.103). Handles of units
      [*] = ;            // are valid only inside one match, and these parsers live in the process:
      [*] = ;            //   br_hgrp  - the roll of every numbered group, handle by handle;
      [*] = ;            //   br_hwave - how many went in the last wave;
      [*] = ;            //   br_kills - the ring of death events;
      [*] = ;            //   br_hstate - the per-slot stamp of when state was last written;
      [*] = ;            //   br_hfail, br_hlog - what the command block refused and said.
      [*] = ;            // Found by a live game: a match against a HUMAN started in the same process
      [*] = ;            // right after a match against the native AI froze the state block at game
      [*] = ;            // second 27-33 for BOTH human slots - the tick lived, the pulse kept writing,
      [*] = ;            // and the state file stayed complete at second 33 forever. The groups section
      [*] = ;            // of the state block switches on together with the grid, that is exactly when
      [*] = ;            // the town hall goes up - 27-33 seconds in - and it walked the OLD match's
      [*] = ;            // handles. Nothing said a word, because a handle that resolves to garbage is
      [*] = ;            // not an error the engine reports.
      [*] = ;            // Cleared BEFORE DoNewGame on purpose: after it the map is already loading and
      [*] = ;            // the first ticks of the new match can run before we get back here.
      [*] = ;            var brnp : Integer;
      [*] = ;            brnp := ParserSelectByKey('br_hgrp');
      [*] = ;            if (brnp <> 0) then ParserClearByHandle(brnp);
      [*] = ;            brnp := ParserSelectByKey('br_hwave');
      [*] = ;            if (brnp <> 0) then ParserClearByHandle(brnp);
      [*] = ;            brnp := ParserSelectByKey('br_kills');
      [*] = ;            if (brnp <> 0) then ParserClearByHandle(brnp);
      [*] = ;            brnp := ParserSelectByKey('br_hstate');
      [*] = ;            if (brnp <> 0) then ParserClearByHandle(brnp);
      [*] = ;            brnp := ParserSelectByKey('br_hfail');
      [*] = ;            if (brnp <> 0) then ParserClearByHandle(brnp);
      [*] = ;            brnp := ParserSelectByKey('br_hlog');
      [*] = ;            if (brnp <> 0) then ParserClearByHandle(brnp);
      [*] = ;            Log('bridge-human: NEW - memory of the previous match cleared');
      [*] = ;            GUIExecuteState('DoNewGame');
      [*] = ;         end;
      [*] = ;         ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;   // === END BRIDGE LOOP ===