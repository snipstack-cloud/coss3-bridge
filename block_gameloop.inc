      [*] = ;   // === BRIDGE LOOP: episode control, game side ===
      [*] = ;   // Lives here and not in the interface actor: reading files compiles
      [*] = ;   // only on this side. The interface is reached through GUIExecuteState,
      [*] = ;   // the same way lib/miscext3.script does it.
      [*] = ;   if (plind = GetPlayerIndexInterfaceIO) and (not _net_IsClient) and (not _net_IsReplay) then
      [*] = ;   begin
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
      [*] = ;         // The UI list numbers levels from 1 (0 means 'slot open'),
      [*] = ;         // while aidifficulty holds one less: showcustomgame.inc:647
      [*] = ;         // sets the list index to aidifficulty+1. So Impossible is 3.
      [*] = ;         // Names come from locale/en/gui.txt: 0 None, 1 Normal,
      [*] = ;         // 2 Hard, 3 Very Hard, 4 Impossible.
      [*] = ;         var brctlnat   : String;         // country sid, 'net' = Netherlands
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
      [*] = ;            if (ParserGetValueByKeyByHandle(hctl, 'speed') <> '') then
      [*] = ;            brctlspd := ParserGetIntValueByKeyByHandle(hctl, 'speed');
      [*] = ;            brctlnat := ParserGetValueByKeyByHandle(hctl, 'nation');
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
      [*] = ;               if (brctlnat <> '') then
      [*] = ;               gMap.players[1].cid := _country_GetIDBySID(brctlnat);
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
      [*] = ;            ParserSetIntValueByKeyByHandle(back, 'speed', floor(GetTimeSpeedFactor));
      [*] = ;            ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;            GUIExecuteState('DoNewGame');
      [*] = ;         end;
      [*] = ;         ParserSaveToFileByHandle(back, '@@OUT@@coss3_ack.dat');
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;   // === END BRIDGE LOOP ===