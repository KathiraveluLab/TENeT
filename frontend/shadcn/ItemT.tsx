import { BadgeCheckIcon, ChevronRightIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from "@/components/ui/item"

export function ItemT({value,dest}) {
  return (
    <div className="flex w-full max-w-md flex-col gap-6">
      <Item variant="outline" size="sm" asChild>
        <a href={dest}>
          <ItemMedia>
            {/* <BadgeCheckIcon className="size-5" /> */}
          </ItemMedia>
          <ItemContent>
            <ItemTitle>{value}</ItemTitle>
            
          </ItemContent>
          <ItemActions>
            <ChevronRightIcon className="size-4" />
          </ItemActions>
        </a>
      </Item>
    </div>
  )
}
