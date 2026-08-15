/*==============================================================
07_artist_fun_facts.sql

Updates:
    - fun_fact

NOTE:
Fun facts are manually maintained and are intended to add
personality to artist tooltips.
==============================================================*/

UPDATE artist_summary
SET artist_note =
CASE artist_name

    WHEN 'Taylor Swift' THEN "The numbers say Taylor Swift is my #1 artist, but I'd call myself a casual listener at most, and I've actually removed a lot of her music from my playlists recently."
    WHEN 'Sleep Token' THEN "First played on 1/25/2023, but the real obsession didn't start until December 2024. Since then, Sleep Token has climbed to the #2 of all-time spot in less than a year and a half and will no doubt be #1 soon enough."
    WHEN 'Shinedown' THEN "Shinedown has been a constant since 2008, a true all-time favorite. Their 2018 album ATTENTION ATTENTION took over my rotation for months after it released. Just saw them live for the first time in 2025 at Welcome to Rockville, Daytona Beach."
    WHEN 'Fall Out Boy' THEN "On rotation since middle school and still going strong. Fall Out Boy is a genuine all-time favorite, proven by two unforgettable live shows. It was never a phase."

    ELSE NULL

END;