<h1>Metal & Lace</h1>
<img width="165" height="229" align="right" src="https://raw.githubusercontent.com/DerekPascarella/MetalAndLace-EnglishPatchFMTowns/main/images/cover_front_small.jpg?token=GHSAT0AAAAAABY4UP7EEYD2EPMSL75CNTC4Y74T3QA">English translation patch for the FM Towns/FM Towns Marty game "Metal & Lace".
<br><br>
Players assume the role of Mimi, a young girl obsessed with developing high-tech remote-controlled robots, known as Silhouettes.  When she and her mother stumble upon an online ad for an underground fighting tournament, her mother quickly decides that Mimi must compete (and win) in order to pay off the tremendous debts that her daughter's hobby has incurred.
<br><br>
What follows is a battle between Mimi and six other girls, all of whom wield their own Silhouettes.  The player completes the game after successfully defeating all six opponents, resulting in a scene where Mimi's mother decides that her daughter must now move on to an even bigger tournament with even bigger prize winnings.
<br><br>
The latest version of this patch is <a href="https://github.com/DerekPascarella/MetalAndLace-EnglishPatchFMTowns/releases/download/0.9/v0.9.zip">0.9</a>.

<h2>Table of Contents</h2>

1. [Patching Instructions](#patching-instructions)
2. [Release Changelog](#release-changelog)
3. [What's Changed](#whats-changed)
4. [To-Do](#to-do)
5. [About the Game](#about-the-game)
6. [How to Play](#how-to-play)

<h2>Patching Instructions</h2>
<img align="right" width="250" src="https://i.imgur.com/r4b04e7.png">The XDelta patch file shipped with this release can be used with any number of Delta utilities, such as <a href="https://www.romhacking.net/utilities/704/">Delta Patcher</a>. Ensure that the <a href="http://redump.org/disc/72696/">Redump version of the game</a> is used as the source disc image, where <tt>Ningyou Tsukai (Japan).bin</tt> has an MD5 checksum of <tt>899AA0A1D3AF956F2A59A4E8638558AE</tt>.
<br><br>
<ol type="1">
<li>Click the settings icon (appears as a gear) and enable "Backup original file" and "Checksum validation".</li>
<li>Click the "Original file" browse icon and select the unmodified <tt>Ningyou Tsukai (Japan).bin</tt> file.</li>
<li>Click the "XDelta patch" browse icon and select the XDelta patch.</li>
<li>Click "Apply patch" to generate the patched <tt>.bin</tt> in the same folder from which the application is launched.</li>
<li>Verify that the patched <tt>.bin</tt> has an MD5 checksum of <tt>DC140C7056E8EBE51983882160E2BF70</tt>.</li>
</ol>

<h2>Release Changelog</h2>
<ul>
 <li>Version 0.9 (2023-02-27)</li>
 <ul>
  <li>Initial release.</li>
 </ul>
</ul>

<h2>What's Changed</h2>
<ul>
<li>Title screen menu text has been translated into English.</li>
<li>Introduction sequence between Mimi and her mother has been translated into English.</li>
<li>Fighter data sheets have been translated into English.</li>
<li>Pre-battle dialogue text has been translated into English.</li>
<li>Mid-battle dialogue text has been translated into English.</li>
<li>Post-battle dialogue text has been translated into English.</li>
<li>Credits have been translated into English.</li>
<li>A missing piece of mid-battle dialogue text has been restored (i.e., bugfix for the original Japanese release).</li>
</ul>

<h2>To-Do</h2>
Due to the game's use of compression when storing its graphics, two items remain untranslated as of version 0.9 of this patch.
<br><br>
<ul>
<li><b>Title Screen Logo</b><br><br><img width="300" height="225" src="xxxx"><br><br></li>
<li><b>Introduction Screen Text</b><br><br><img width="300" height="225" src="xxxx"><br><br><i>Silhouettes are remote-controlled robots originally developed to work in harsh conditions, such as outer space.  However, these robots quickly became popular for other applications, including combat.  The rise is this robot-on-robot form of martial arts resulted in numerous tournaments being held, including a world championship.</i></li>
</ul>

<h2>About the Game</h2>
<table>
<tr>
<td><b>Original Title</b></td>
<td>Ningyou Tsukai (人形使い)</td>
</tr>
<tr>
<td><b>Localized Title</b></td>
<td>Metal & Lace</td>
</tr>
<tr>
<td><b>Developer</b></td>
<td>Forest</td>
</tr>
<tr>
<td><b>Publisher</b></td>
<td>Forest</td>
</tr>
<tr>
<td><b>Release Date</b></td>
<td>October 1993</td>
</tr>
<tr>
<td><b>Compatibility</b></td>
<td>FM Towns<br>FM Towns Marty (with mild color palette issues)</td>
</tr>
</table>

<h2>How to Play</h2>
<ul>
 <li><b>ODE (Optical Drive Emulator)</b><br>The English-patched version of this game is compatible with both the <a href="https://gdemu.wordpress.com/details/docbrown-details/">DocBrown</a> and <a href="https://gdemu.wordpress.com/details/wizard-details/">Wizard</a> ODEs for the FM Towns Marty and the FM Towns, respectively.  Note that only the patched <tt>.bin</tt> file should be copied to the SD card, as neither ODE supports parsing CUE sheets.  Because "Metal & Lace" uses only one data track with no CDDA, both of these ODEs are compatible with the single <tt>.bin</tt>.<br><br>In order to save game progress, an MS-DOS-formatted floppy disk must be present.  For users of FDD emulators (e.g., <a href="https://www.gotekemulator.com/">GoTek</a>, <a href="https://caiusarcade.blogspot.com/2021/05/the-thing-fm-towns-marty-fdd-emulator.html">The Thing</a>), see pre-made disk images below.<br><br>⯈ <a href="https://github.com/DerekPascarella/MetalAndLace-EnglishPatchFMTowns/blob/main/fdd_images/Blank%20Disk%20(MS-DOS%20Formatted).hfe">Blank Disk (MS-DOS Formatted).hfe</a><br>⯈ <a href="https://github.com/DerekPascarella/MetalAndLace-EnglishPatchFMTowns/blob/main/fdd_images/Metal%20%26%20Lace%20-%20Completed%20Save.hfe">Metal & Lace - Completed Save.hfe</a><br><br></li>
 <li><b>Emulator</b><br>The English-patched version of this game is compatible with the <a href="https://github.com/captainys/TOWNSEMU">Tsugaru</a> emulator, and likely <a href="http://townsemu.world.coocan.jp/download.html">Unz</a> as well.  In order to save game progress, an MS-DOS-formatted floppy disk must be present.  The following pre-made disk images have been tested and confirmed working with Tsugaru.<br><br>⯈ <a href="https://github.com/DerekPascarella/MetalAndLace-EnglishPatchFMTowns/blob/main/fdd_images/Blank%20Disk%20(MS-DOS%20Formatted).d88">Blank Disk (MS-DOS Formatted).d88</a><br>⯈ <a href="https://github.com/DerekPascarella/MetalAndLace-EnglishPatchFMTowns/blob/main/fdd_images/Metal%20%26%20Lace%20-%20Completed%20Save.d88">Metal & Lace - Completed Save.d88</a></li>
</ul>
