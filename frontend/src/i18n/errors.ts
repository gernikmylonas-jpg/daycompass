import axios from 'axios'
import { i18n } from './index'

// The backend answers with English `detail` strings. Map the known ones to translated
// messages; capture group 1 (if any) becomes the {n} parameter.
const RULES: [RegExp, string][] = [
  [/^Invalid invite code$/, 'invalidInviteCode'],
  [/^Already a member of this group$/, 'alreadyMember'],
  [/^Habit not found$/, 'habitNotFound'],
  [/^Group not found$/, 'groupNotFound'],
  [/^User not found$/, 'userNotFound'],
  [/^Email already registered$/, 'emailRegistered'],
  [/^Already checked in today$/, 'alreadyCheckedIn'],
  [/^Only the owner can delete the group$/, 'ownerOnly'],
  [/^Invalid category$/, 'invalidCategory'],
  [/^Invalid kind$/, 'invalidKind'],
  [/^Invalid email or password$/, 'invalidCredentials'],
  [/^Invalid (or expired )?token$/, 'invalidSession'],
  [/^Name (is required|cannot be empty)$/, 'nameRequired'],
  [/^Name is too long \(max (\d+) characters\)$/, 'nameTooLong'],
  [/^Description is too long \(max (\d+) characters\)$/, 'descriptionTooLong'],
  [/^Title is too long \(max (\d+) characters\)$/, 'titleTooLong'],
  [/^Duration must be between 1 and 180 minutes$/, 'durationRange'],
  [/^Date cannot be in the future$/, 'futureDate'],
  [/^Date cannot be older than (\d+) days$/, 'dateTooOld'],
  [/^Steps must be between 0 and (\d+)$/, 'stepsRange'],
  [/^Sleep must be between 0 and 24 hours$/, 'sleepRange'],
  [/^Quality must be between 1 and 5$/, 'qualityRange'],
  [/^End date must not be before start date$/, 'endBeforeStart'],
  [/^Range is limited to (\d+) days$/, 'rangeLimited'],
  [/^Period must be /, 'periodInvalid'],
  [/^Event not found$/, 'eventNotFound'],
  [/^Too many events$/, 'tooManyEvents'],
  [/^Year must be between /, 'yearRange'],
  [/^Notes are too long \(max (\d+) characters\)$/, 'notesTooLong'],
  [/^Invalid (theme|mode|language|mood style|brightness)$/, 'invalidSetting'],
  [/^Current password is incorrect$/, 'wrongPassword'],
  [/^Password must be at least (\d+) characters$/, 'passwordShort'],
  [/^The new password must be different$/, 'passwordSame'],
  [/^Score must be between 1 and 10$/, 'scoreRange'],
  [/^Note is too long \(max (\d+) characters\)$/, 'noteTooLong'],
  [/^Date cannot be before 2000$/, 'dateBefore2000'],
  [/^Entry not found$/, 'journalNotFound'],
  [/^Write something or record audio$/, 'journalEmpty'],
  [/^Entry is too long \(max (\d+) characters\)$/, 'journalTooLong'],
  [/^Invalid mood$/, 'invalidMood'],
  [/^Recording is too large/, 'audioTooLarge'],
  [/^Unsupported audio type$/, 'audioType'],
  [/^Recording not found$/, 'audioNotFound'],
  [/^Rest days can be set from /, 'restDayRange'],
  [/^Too many rest days: at most (\d+)/, 'restDaysMax'],
  [/^Rest day not found$/, 'restNotFound'],
  [/^Journal is locked$/, 'journalLocked'],
  [/^Wrong journal PIN$/, 'wrongPin'],
  [/^PIN must be at least (\d+) characters$/, 'pinShort'],
  [/^Journal lock already enabled$/, 'lockExists'],
  [/^Journal lock is not enabled$/, 'lockNotEnabled'],
  [/^Challenge not found$/, 'challengeNotFound'],
  [/^Only the owner can manage challenges$/, 'challengeOwner'],
  [/^Invalid metric$/, 'invalidMetric'],
  [/^Target must be between 1 and (\d+)$/, 'targetRange'],
  [/^Too many challenges$/, 'tooManyChallenges'],
  [/^Invalid frequency$/, 'invalidFrequency'],
  [/^Unknown country$/, 'unknownCountry'],
  [/^Push notifications are not set up on this server$/, 'pushNotSetUp'],
  [/^Too many devices$/, 'tooManyDevices'],
  [/^Invalid subscription$/, 'invalidSubscription'],
  [/^Too many attempts/, 'tooManyAttempts'],
  [/^Only the creator or the group owner can delete this habit$/, 'habitDeleteDenied'],
  [/^Already done$/, 'alreadyDone'],
  [/^Range is limited to 366 days$/, 'rangeLimited'],
  [/^Too many shared habits$/, 'tooManySharedHabits'],
  [/^Invalid emoji$/, 'invalidEmoji'],
  [/^Choose someone else in the group$/, 'cheerSelf'],
  [/^You already cheered them today$/, 'cheerOnce'],
  [/^Glasses must be between 0 and (\d+)$/, 'glasses'],
  [/^Minutes must be between 1 and (\d+)$/, 'workoutMinutes'],
  [/^At most (\d+) entries a day$/, 'gratitudeDay'],
  [/^Write something first$/, 'writeFirst'],
  [/^Quest is not finished yet$/, 'questLater'],
  [/^Quest reward already claimed$/, 'questClaimed'],
  [/^Unsupported image type$/, 'imageType'],
  [/^Picture is too large/, 'imageBig'],
  [/^No profile photo$/, 'noPhoto'],
  [/^Goal not found$/, 'goalNotFound'],
  [/^Too many goals$/, 'tooManyGoals'],
  [/^Wallpaper not found$/, 'wallpaperNotFound'],
  [/^Wallpaper already unlocked$/, 'wallpaperOwned'],
  [/^Not enough nuggets$/, 'notEnough'],
  [/^Wallpaper is not unlocked$/, 'wallpaperLocked'],
  [/^Weight must be between (\d+) and (\d+) kg$/, 'weightRange'],
  [/^Height must be between (\d+) and (\d+) cm$/, 'heightRange'],
  [/^Invalid unit$/, 'invalidUnit'],
  [/^Choose yearly or weekly repeat/, 'repeatBoth'],
  [/^Invalid calendar preferences$/, 'invalidSetting'],
]

export function apiErrorMessage(e: unknown): string {
  const { t } = i18n.global
  if (!axios.isAxiosError(e) || !e.response) return t('common.genericError')

  const detail = e.response.data?.detail
  if (typeof detail === 'string') {
    for (const [pattern, key] of RULES) {
      const match = pattern.exec(detail)
      if (match) {
        // the {n} parameter is the last captured number, when the rule has one
        const n = [...match].slice(1).reverse().find((g) => g && /^\d+$/.test(g))
        return t(`errors.${key}`, { n: n ?? '' })
      }
    }
  }
  // FastAPI validation errors (e.g. a malformed email) arrive as a list
  if (e.response.status === 422) return t('errors.invalidInput')
  return t('common.genericError')
}
