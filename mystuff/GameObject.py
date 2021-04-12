from panda3d.core import Vec3, Vec2, Vec4, CollisionSphere, CollisionNode, CollisionTraverser, CollisionHandlerPusher, CollisionRay, CollisionHandlerQueue, BitMask32, Plane, Point3, CollisionSegment, TextNode, PointLight, AudioSound
from direct.actor.Actor import Actor
import math
import random
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage


FRICTION = 150.0


class GameObject():
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName):
        self.actor = Actor(modelName, modelAnims)
        self.actor.reparentTo(render)
        self.actor.setPos(pos)

        self.maxHealth = maxHealth
        self.health = maxHealth

        self.maxSpeed = maxSpeed

        self.velocity = Vec3(0, 0, 0)
        self.acceleration = 300.0

        self.walking = False

        colliderNode = CollisionNode(colliderName)
        colliderNode.addSolid(CollisionSphere(0, 0, 0, 0.3))
        self.collider = self.actor.attachNewNode(colliderNode)
        self.collider.setPythonTag("owner", self)
        # print(self.collider)

        self.deathSound = None

    def update(self, dt):
        speed = self.velocity.length()
        if speed > self.maxSpeed:
            self.velocity.normalize()
            self.velocity *= self.maxSpeed
            speed = self.maxSpeed

        if not self.walking:
            frictionVal = FRICTION*dt
            if frictionVal > speed:
                self.velocity.set(0, 0, 0)
            else:
                frictionVec = -self.velocity
                frictionVec.normalize()
                frictionVec *= frictionVal

                self.velocity += frictionVec

        self.actor.setPos(self.actor.getPos() + self.velocity*dt)

    def alterHealth(self, dHealth):
        previousHealth = self.health

        self.health += dHealth

        if self.health > self.maxHealth:
            self.health = self.maxHealth

        if previousHealth > 0 and self.health <= 0 and self.deathSound is not None:
            self.deathSound.play()

    def cleanup(self):
        # print("clean up")
        if self.collider is not None and not self.collider.isEmpty():
            self.collider.clearPythonTag("owner")
            base.cTrav.removeCollider(self.collider)
            base.pusher.removeCollider(self.collider)

        if self.actor is not None:
            self.actor.cleanup()
            self.actor.removeNode()
            self.actor = None

        self.collider = None


class Player(GameObject):
    def __init__(self):
        # print("Player1")
        GameObject.__init__(self, Vec3(0, 0, 0), "models/PandaChan/act_p3d_chan", {
                            "stand": "models/PandaChan/a_p3d_chan_idle", "walk": "models/PandaChan/a_p3d_chan_run"}, 5, 10, "player")

        self.actor.getChild(0).setH(180)

        mask = BitMask32()
        mask.setBit(1)

        self.collider.node().setIntoCollideMask(mask)

        mask = BitMask32()
        mask.setBit(1)

        self.collider.node().setFromCollideMask(mask)

        self.cTrav = CollisionTraverser()
        self.pusher = CollisionHandlerPusher()

        # print(self.actor)

        base.pusher.addCollider(self.collider, self.actor)
        base.cTrav.addCollider(self.collider, base.pusher)

        self.actor.loop("stand")

        self.ray = CollisionRay(0, 0, 0, 0, 1, 0)

        rayNode = CollisionNode("playerRay")
        rayNode.addSolid(self.ray)

        self.rayNodePath = render.attachNewNode(rayNode)
        self.rayQueue = CollisionHandlerQueue()

        base.cTrav.addCollider(self.rayNodePath, self.rayQueue)

        mask = BitMask32()
        mask.setBit(2)
        rayNode.setFromCollideMask(mask)

        mask = BitMask32()
        rayNode.setIntoCollideMask(mask)

        self.damagePerSecond = -5.0

        self.beamModel = loader.loadModel("models/laser/bambooLaser")
        self.beamModel.reparentTo(self.actor)
        self.beamModel.setZ(1.5)
        self.beamModel.setLightOff()
        self.beamModel.hide()

        self.lastMousePos = Vec2(0, 0)

        self.groundPlane = Plane(Vec3(0, 0, 1), Vec3(0, 0, 0))

        self.yVector = Vec2(0, 1)

        self.score = 0
        self.font = loader.loadFont("fonts/Wbxkomik.ttf")

        self.scoreUI = OnscreenText(
            text="0", pos=(-1.3, 0.825), mayChange=True, align=TextNode.ALeft, font=self.font)

        self.healthIcons = []
        for i in range(self.maxHealth):
            icon = OnscreenImage(image="UI/health.png",
                                 pos=(-1.275 + i * 0.075, 0, 0.95), scale=0.04)
            icon.setTransparency(True)
            self.healthIcons.append(icon)

        self.beamHitModel = loader.loadModel("models/laser/bambooLaserHit")
        self.beamHitModel.reparentTo(render)
        self.beamHitModel.setZ(1.5)
        self.beamHitModel.setLightOff()
        self.beamHitModel.hide()

        self.beamHitPulseRate = 0.15
        self.beamHitTimer = 0

        self.beamHitLight = PointLight("beamHitLight")
        self.beamHitLight.setColor(Vec4(0.1, 1.0, 0.2, 1))

        self.beamHitLight.setAttenuation((1.0, 0.1, 0.5))
        self.beamHitLightNodePath = render.attachNewNode(self.beamHitLight)

        self.damageTakenModel = loader.loadModel("models/laser/playerHit")
        self.damageTakenModel.setLightOff()
        self.damageTakenModel.setZ(1.0)
        self.damageTakenModel.reparentTo(self.actor)
        self.damageTakenModel.hide()

        self.damageTakenModelTimer = 0
        self.damageTakenModelDuration = 0.15

        self.laserSoundNoHit = loader.loadSfx("music/Sounds_laserNoHit.ogg")
        self.laserSoundNoHit.setLoop(True)
        self.laserSoundHit = loader.loadSfx("music/Sounds_laserHit.ogg")
        self.laserSoundHit.setLoop(True)
        self.hurtSound = loader.loadSfx("music/Sounds_FemaleDmgNoise.ogg")

    def update(self, keys, dt):
        GameObject.update(self, dt)

        self.walking = False

        # print(keys)
        if keys["up"]:
            self.walking = True
            self.velocity.addY(self.acceleration*dt)
            self.actor.getChild(0).setH(180)
        if keys["down"]:
            self.walking = True
            self.velocity.addY(-self.acceleration*dt)
            self.actor.getChild(0).setH(0)
        if keys["left"]:
            self.walking = True
            self.velocity.addX(-self.acceleration*dt)
            self.actor.getChild(0).setH(-90)
        if keys["right"]:
            self.walking = True
            self.velocity.addX(self.acceleration*dt)
            self.actor.getChild(0).setH(90)
        if keys["shoot"]:
            if self.rayQueue.getNumEntries() > 0:
                scoreHit = False
                self.rayQueue.sortEntries()
                rayHit = self.rayQueue.getEntry(0)
                hitPos = rayHit.getSurfacePoint(render)
                hitNodePath = rayHit.getIntoNodePath()
                # print(hitNodePath)
                if hitNodePath.hasPythonTag("owner"):
                    hitObject = hitNodePath.getPythonTag("owner")
                    if not isinstance(hitObject, TrapEnemy):
                        hitObject.alterHealth(self.damagePerSecond*dt)
                        scoreHit = True

                beamLength = (hitPos - self.actor.getPos()).length()
                self.beamModel.setSy(beamLength)
                self.beamModel.show()

                if scoreHit:
                    if self.laserSoundNoHit.status() == AudioSound.PLAYING:
                        self.laserSoundNoHit.stop()
                    if self.laserSoundHit.status() != AudioSound.PLAYING:
                        self.laserSoundHit.play()
                    self.beamHitModel.show()
                    self.beamHitModel.setPos(hitPos)
                    self.beamHitLightNodePath.setPos(hitPos + Vec3(0, 0, 0.5))

                    if not render.hasLight(self.beamHitLightNodePath):
                        render.setLight(self.beamHitLightNodePath)
                else:
                    if self.laserSoundHit.status() == AudioSound.PLAYING:
                        self.laserSoundHit.stop()
                    if self.laserSoundNoHit.status() != AudioSound.PLAYING:
                        self.laserSoundNoHit.play()
                    if render.hasLight(self.beamHitLightNodePath):
                        render.clearLight(self.beamHitLightNodePath)
                    self.beamHitModel.hide()
        else:
            if self.laserSoundNoHit.status() == AudioSound.PLAYING:
                self.laserSoundNoHit.stop()
            if self.laserSoundHit.status() == AudioSound.PLAYING:
                self.laserSoundHit.stop()
            if render.hasLight(self.beamHitLightNodePath):
                render.clearLight(self.beamHitLightNodePath)
            self.beamModel.hide()
            self.beamHitModel.hide()

        if self.walking:
            standControl = self.actor.getAnimControl("stand")
            if standControl.isPlaying():
                standControl.stop()

            walkControl = self.actor.getAnimControl("walk")
            if not walkControl.isPlaying():
                self.actor.loop("walk")
        else:
            standControl = self.actor.getAnimControl("stand")
            if not standControl.isPlaying():
                self.actor.stop("walk")
                self.actor.loop("stand")

        mouseWatcher = base.mouseWatcherNode
        if mouseWatcher.hasMouse():
            mousePos = mouseWatcher.getMouse()
        else:
            mousePos = self.lastMousePos

        mousePos3D = Point3()
        nearPoint = Point3()
        farPoint = Point3()

        base.camLens.extrude(mousePos, nearPoint, farPoint)

        self.groundPlane.intersectsLine(mousePos3D, render.getRelativePoint(
            base.camera, nearPoint), render.getRelativePoint(base.camera, farPoint))

        firingVector = Vec3(mousePos3D - self.actor.getPos())
        firingVector2D = firingVector.getXy()
        firingVector2D.normalize()
        firingVector.normalize()

        heading = self.yVector.signedAngleDeg(firingVector2D)

        self.actor.setH(heading)

        if firingVector.length() > 0.001:
            self.ray.setOrigin(self.actor.getPos())
            self.ray.setDirection(firingVector)

        self.lastMousePos = mousePos

        self.beamHitTimer -= dt
        if self.beamHitTimer <= 0:
            self.beamHitTimer = self.beamHitPulseRate
            self.beamHitModel.setH(random.uniform(0.0, 360.0))
        self.beamHitModel.setScale(
            math.sin(self.beamHitTimer*3.142/self.beamHitPulseRate)*0.4 + 0.9)

        if self.damageTakenModelTimer > 0:
            self.damageTakenModelTimer -= dt
            self.damageTakenModel.setScale(
                2.0 - self.damageTakenModelTimer/self.damageTakenModelDuration)
            if self.damageTakenModelTimer <= 0:
                self.damageTakenModel.hide()

    def cleanup(self):
        base.cTrav.removeCollider(self.rayNodePath)

        GameObject.cleanup(self)

        self.scoreUI.removeNode()

        for icon in self.healthIcons:
            icon.removeNode()

        self.beamHitModel.removeNode()

        render.clearLight(self.beamHitLightNodePath)
        self.beamHitLightNodePath.removeNode()

        self.laserSoundHit.stop()
        self.laserSoundNoHit.stop()

    def updateScore(self):
        self.scoreUI.setText(str(self.score))

    def alterHealth(self, dHealth):
        GameObject.alterHealth(self, dHealth)
        self.updateHealthUI()

        self.damageTakenModel.show()
        self.damageTakenModel.setH(random.uniform(0.0, 360.0))
        self.damageTakenModelTimer = self.damageTakenModelDuration

        self.hurtSound.play()

    def updateHealthUI(self):
        for index, icon in enumerate(self.healthIcons):
            if index < self.health:
                icon.show()
            else:
                icon.hide()


class Enemy(GameObject):
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName):
        GameObject.__init__(self, pos, modelName, modelAnims,
                            maxHealth, maxSpeed, colliderName)

        self.scoreValue = 1

    def update(self, player, dt):

        GameObject.update(self, dt)

        self.runLogic(player, dt)

        if self.walking:
            walkingControl = self.actor.getAnimControl("walk")
            if not walkingControl.isPlaying():
                self.actor.loop("walk")
        else:
            spawnControl = self.actor.getAnimControl("spawn")
            if spawnControl is None or not spawnControl.isPlaying():
                attackControl = self.actor.getAnimControl("attack")
                if attackControl is None or not attackControl.isPlaying():
                    standControl = self.actor.getAnimControl("stand")
                    if not standControl.isPlaying():
                        self.actor.loop("stand")

    def runLogic(self, player, dt):
        pass


class WalkingEnemy(Enemy):
    def __init__(self, pos):
        Enemy.__init__(self, pos, "models/enemy/simpleEnemy", {"stand": "models/enemy/simpleEnemy-stand", "walk": "models/enemy/simpleEnemy-walk",
                       "attack": "models/enemy/simpleEnemy-attack", "die": "models/enemy/simpleEnemy-die", "spawn": "models/enemy/simpleEnemy-spawn"}, 3.0, 7.0, "walkingEnemy")

        mask = BitMask32()
        mask.setBit(2)

        self.collider.node().setIntoCollideMask(mask)

        self.attackDistance = 0.75

        self.acceleration = 100.0

        self.yVector = Vec2(0, 1)

        self.attackSegment = CollisionSegment(0, 0, 0, 1, 0, 0)

        segmentNode = CollisionNode("enemyAttactSegment")
        segmentNode.addSolid(self.attackSegment)

        mask = BitMask32()
        mask.setBit(1)

        segmentNode.setFromCollideMask(mask)

        mask = BitMask32()

        segmentNode.setIntoCollideMask(mask)

        self.attackSegmentNodePath = render.attachNewNode(segmentNode)
        self.segmentQueue = CollisionHandlerQueue()

        base.cTrav.addCollider(self.attackSegmentNodePath, self.segmentQueue)

        self.attackDamage = -1

        self.attackDelay = 0.3
        self.attackDelayTimer = 0

        self.attackDWaitTimer = 0

        self.actor.play("spawn")

        self.deathSound = loader.loadSfx("music/Sounds_enemyDie.ogg")
        self.attackSound = loader.loadSfx("music/Sounds_enemyAttack.ogg")

    def runLogic(self, player, dt):

        spawnControl = self.actor.getAnimControl("spawn")
        if spawnControl is not None and spawnControl.isPlaying():
            return

        vectorToPlayer = player.actor.getPos() - self.actor.getPos()

        vectorToPlayer2D = vectorToPlayer.getXy()
        distanceToPlayer = vectorToPlayer2D.length()

        vectorToPlayer2D.normalize()

        heading = self.yVector.signedAngleDeg(vectorToPlayer2D)

        self.attackSegment.setPointA(self.actor.getPos())
        self.attackSegment.setPointB(
            self.actor.getPos() + self.actor.getQuat().getForward()*self.attackDistance)

        if distanceToPlayer > self.attackDistance*0.9:
            attackControl = self.actor.getAnimControl("attack")
            if not attackControl.isPlaying():
                self.walking = True
                vectorToPlayer.setZ(0)
                vectorToPlayer.normalize()
                self.velocity += vectorToPlayer*self.acceleration*dt
                self.attackWaitTimer = 0.2
                self.attackDelayTimer = 0
        else:
            self.walking = False
            self.velocity.set(0, 0, 0)

            if self.attackDelayTimer > 0:
                self.attackDelayTimer -= dt
                if self.attackDelayTimer <= 0:
                    if self.segmentQueue.getNumEntries() > 0:
                        self.segmentQueue.sortEntries()
                        segmentHit = self.segmentQueue.getEntry(0)

                        hitNodePath = segmentHit.getIntoNodePath()
                        if hitNodePath.hasPythonTag("owner"):
                            hitObject = hitNodePath.getPythonTag("owner")
                            hitObject.alterHealth(self.attackDamage)
                            self.attackWaitTimer = 1.0
            elif self.attackWaitTimer > 0:
                self.attackWaitTimer -= dt
                if self.attackWaitTimer <= 0:
                    self.attackWaitTimer = random.uniform(0.5, 0.7)
                    self.attackDelayTimer = self.attackDelay
                    self.actor.play("attack")
                    self.attackSound.play()

        self.actor.setH(heading)

    def cleanup(self):
        base.cTrav.removeCollider(self.attackSegmentNodePath)
        self.attackSegmentNodePath.removeNode()

        GameObject.cleanup(self)

    def alterHealth(self, dHealth):
        Enemy.alterHealth(self, dHealth)
        self.updateHealthVisual()

    def updateHealthVisual(self):
        perc = self.health/self.maxHealth
        if perc < 0:
            perc = 0
        self.actor.setColorScale(perc, perc, perc, 1)


class TrapEnemy(Enemy):
    def __init__(self, pos):
        Enemy.__init__(self, pos, "models/trap/trap",
                       {"stand": "models/trap/trap-stand", "walk": "models/trap/trap-walk"}, 100.0, 10.0, "trapEnemy")

        mask = BitMask32()
        mask.setBit(2)
        mask.setBit(1)

        self.collider.node().setIntoCollideMask(mask)

        mask = BitMask32()
        mask.setBit(2)
        mask.setBit(1)

        self.collider.node().setFromCollideMask(mask)

        base.pusher.addCollider(self.collider, self.actor)
        base.cTrav.addCollider(self.collider, base.pusher)

        self.movInX = False

        self.moveDirection = 0

        self.ignorePlayer = False

        self.impackSound = loader.loadSfx("music/Sounds_trapHitsSomething.ogg")
        self.stopSound = loader.loadSfx("music/Sounds_trapStop.ogg")
        self.movementSound = loader.loadSfx("music/Sounds_trapSlide.ogg")
        self.movementSound.setLoop(True)

    def runLogic(self, player, dt):
        if self.moveDirection != 0:
            self.walking = True
            if self.movInX:
                self.velocity.addX(self.moveDirection*self.acceleration*dt)
            else:
                self.velocity.addY(self.moveDirection*self.acceleration*dt)
        else:
            self.walking = False
            diff = player.actor.getPos() - self.actor.getPos()
            if self.movInX:
                detector = diff.y
                movement = diff.x
            else:
                detector = diff.x
                movement = diff.y

            if abs(detector) < 0.5:
                self.moveDirection = math.copysign(1, movement)
                self.movementSound.play()

    def cleanup(self):
        self.movementSound.stop()

        Enemy.cleanup(self)

    def alterHealth(self, dHealth):
        pass
