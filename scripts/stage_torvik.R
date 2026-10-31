# Fetch T-Rank adjusted efficiency and tempo without KenPom credentials.
# This is a staging export only: team-name-to-ESPN-ID reconciliation must
# be validated before these ratings can enter the simulator.
suppressPackageStartupMessages(library(toRvik))
suppressPackageStartupMessages(library(jsonlite))
season <- as.integer(format(Sys.Date(), "%Y")) + as.integer(as.integer(format(Sys.Date(), "%m")) >= 7L)
ratings <- toRvik::bart_ratings(year = season)
needed <- c("team", "adj_o", "adj_d", "adj_t")
if (!all(needed %in% names(ratings))) stop("T-Rank schema changed")
ratings <- ratings[, needed]
ratings <- ratings[complete.cases(ratings), ]
if (nrow(ratings) < 300L) stop("Insufficient T-Rank coverage; refusing incomplete export")
if (anyDuplicated(ratings$team)) stop("Duplicate T-Rank team names")
dir.create("data/staging", recursive = TRUE, showWarnings = FALSE)
payload <- list(source = "Bart Torvik T-Rank via toRvik::bart_ratings",
                fetchedAt = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
                season = season, status = "UNMATCHED_DO_NOT_SIMULATE",
                teams = ratings)
write_json(payload, "data/staging/torvik-ratings.json", auto_unbox = TRUE, pretty = TRUE)
cat("Staged", nrow(ratings), "team ratings for", season, "\n")
