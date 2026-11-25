# Recipe: let an agent fill your photo calendar project

The picker ends with 24 door photos and a cover in a folder. You can drag them into your photo service's software by
hand. If you want an AI agent to put them into the project for you, this recipe describes how I did it with BIPA
FotoShop. It works the same way with other desktop software for photo products, as long as the project is a file on
your computer.

The repo has no script for this step. Project files of photo services are not documented, and each service has its
own format, so your agent works it out from your own files.

## Steps

1. In your photo service's software, create the calendar and save it once without photos. This is the template.
2. Put one photo on door 1 and save the project again under a new name.
3. Give both files to the agent and let it compare them: how the file is packed (often a ZIP or SQLite file), where
   the photo itself is stored, and where the crop for each door is written.
4. Let it write a script that takes the template and a list of photos, and writes a new project file. It must never
   write to the template, so a mistake costs you nothing.
5. Open the new file in your photo service's software and check every door and the cover there before you order.

## Prompt

```
I have two saved projects from my photo service's desktop software: [empty file] is an
empty Advent calendar, [one-photo file] is the same calendar with one photo on door 1.
Find out how the project file stores a photo and its crop. Then write a script that takes
the template and the 25 files in the picker's calendar-photos folder (00_cover_... is
the cover, the number in 01_... to 24_... is the door) and writes a new project file with
those photos. Take each crop from calendar-photos/crops.json (left, top, width and height
as fractions of the photo); it holds where I moved the crop in the picker. Never write to
the template. Don't open or look at the photos yourself, run everything on this computer and don't upload anything.
Tell me what you could not work out from the two files. I'll check and adjust the crops
in the software before I order.
```

## What to watch

- **Crops.** The software may add its own margin around a door. Compare a door filled by the script with one you
  filled by hand.
- **File size.** The finished project contains all 25 photos in full size. Some services pad the file to a fixed size,
  and the script has to keep that.
- **Your terms.** Check that your photo service allows editing project files outside its software. I filled the file
  for my own order only.
