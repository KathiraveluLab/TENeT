import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"

export function HoverCardT() {
  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        <Button variant="link" >@TENeT AI</Button>
      </HoverCardTrigger>
      <HoverCardContent className="w-80">
        <div className="flex justify-between gap-4">
          <Avatar>
            <AvatarImage src="https://avatars.githubusercontent.com/u/78570320  " />
            <AvatarFallback>VC</AvatarFallback>
          </Avatar>
          <div className="space-y-1">
            {/* <h4 className="text-sm font-semibold">@nextjs</h4> */}
            <p className="text-sm">
              Telehealth Effectiveness and Necessity Tracker.
            </p>
            <div className="text-muted-foreground text-xs">
              Coming soon
            </div>
          </div>
        </div>
      </HoverCardContent>
    </HoverCard>
  )
}
